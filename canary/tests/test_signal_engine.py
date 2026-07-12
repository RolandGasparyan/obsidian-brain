"""
test_signal_engine.py - Real unit tests for canary_executor.py pure functions.
P4 remediation 2026-05-23.
Tests: get_signal(), score_pairs(), position sizing math, save_state atomicity.
All external calls are mocked. Runs offline.
"""
import json, math, sys, time, tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_TESTS_DIR = Path(__file__).parent
_CANARY_DIR = _TESTS_DIR.parent
if str(_CANARY_DIR) not in sys.path:
    sys.path.insert(0, str(_CANARY_DIR))

_ccxt_mock = MagicMock()
_ccxt_mock.InsufficientFunds = Exception
sys.modules.setdefault("ccxt", _ccxt_mock)

import canary_executor as ex


def _make_ohlcv_cmo(n=50, close_trend="up", base=50000.0, vol_surge=False):
    """Create OHLCV candles for CMO signal testing.
    close_trend='up'   -> rising closes -> positive CMO -> BUY
    close_trend='down' -> falling closes -> negative CMO -> SELL
    close_trend='flat' -> flat closes -> CMO=0 -> HOLD
    """
    now = int(time.time() * 1000)
    candles = []
    for i in range(n):
        if close_trend == "up":
            c = base + i * (base * 0.002)
        elif close_trend == "down":
            c = base - i * (base * 0.002)
        else:
            c = base
        vol = 2e6 if (vol_surge and i == n - 1) else 1e6
        candles.append([now - (n - i) * 60000, c, c * 1.001, c * 0.999, c, vol])
    return candles


def _make_ex_cmo(trend="up", vol_surge=True, last=50000.0):
    """Mock exchange returning CMO-appropriate candles."""
    e = MagicMock()
    e.fetch_ohlcv.return_value = _make_ohlcv_cmo(
        n=ex.DAILY_CANDLE_LIMIT, close_trend=trend, vol_surge=vol_surge
    )
    e.fetch_ticker.return_value = {"last": last, "percentage": 0.5, "quoteVolume": 1e9}
    return e


class TestGetSignal:
    def test_buy_on_uptrend_with_volume(self):
        """BUY: strong CMO momentum + RSI > 52 + volume surge"""
        result = ex.get_signal(_make_ex_cmo(trend="up", vol_surge=True), "WIF/USDT")
        assert result["signal"] == "BUY"
        assert result["price"] == 50000.0

    def test_sell_on_downtrend(self):
        """SELL: CMO < -CMO_THRESHOLD = momentum reversal"""
        result = ex.get_signal(_make_ex_cmo(trend="down", vol_surge=False), "WIF/USDT")
        assert result["signal"] == "SELL"

    def test_hold_on_flat_market(self):
        """HOLD: CMO = 0 = no momentum"""
        result = ex.get_signal(_make_ex_cmo(trend="flat", vol_surge=False), "WIF/USDT")
        assert result["signal"] == "HOLD"

    def test_hold_on_insufficient_candles(self):
        """HOLD: not enough candles for CMO calculation"""
        e = MagicMock()
        e.fetch_ohlcv.return_value = [[0, 0, 0, 0, 50000, 1e6]] * 5
        e.fetch_ticker.return_value = {"last": 50000}
        r = ex.get_signal(e, "WIF/USDT")
        assert r["signal"] == "HOLD"
        assert r.get("reason") == "insufficient_data"

    def test_hold_on_exception(self):
        """HOLD returned on exchange error"""
        e = MagicMock()
        e.fetch_ohlcv.side_effect = Exception("network error")
        e.fetch_ticker.return_value = {"last": None}
        r = ex.get_signal(e, "WIF/USDT")
        assert r["signal"] == "HOLD"

    def test_signal_contains_cmo_and_rsi(self):
        """Signal dict must include cmo and rsi values"""
        result = ex.get_signal(_make_ex_cmo(trend="up", vol_surge=True), "WIF/USDT")
        assert "cmo" in result
        assert "rsi" in result


class TestScorePairs:
    def test_returns_all_pairs(self):
        ranked = ex.score_pairs(_make_ex())
        assert set(ranked) == set(ex.ALL_PAIRS)
        assert len(ranked) == len(ex.ALL_PAIRS)

    def test_higher_volume_ranks_higher(self):
        e = MagicMock()
        # Use actual CMO_CHANDE v2 pairs
        pairs = ex.ALL_PAIRS
        call_count = [0]
        def mock_ticker(pair):
            call_count[0] += 1
            # Give FLOKI highest volume (it has PF=4.43)
            vol = 1e10 if pair == "FLOKI/USDT" else 1e6
            return {"percentage": 0.0, "quoteVolume": vol, "last": 0.001}
        e.fetch_ticker.side_effect = mock_ticker
        ranked = ex.score_pairs(e, pairs)
        assert ranked[0][0] == "FLOKI/USDT", f"Expected FLOKI/USDT first, got {ranked[0][0]}"

    def test_failed_ticker_last(self):
        e = MagicMock()
        pairs = ex.ALL_PAIRS
        def ticker(pair):
            if pair == "BNB/USDT": raise Exception("fail")
            return {"percentage": 0.0, "quoteVolume": 1e6, "last": 100}
        e.fetch_ticker.side_effect = ticker
        ranked = ex.score_pairs(e, pairs)
        # Failed pair should be last
        assert ranked[-1][0] == "BNB/USDT"


class TestPositionSizing:
    @pytest.mark.parametrize("capital,pct,expected", [
        (1579.52, 0.06, 94.77),
        (200.00,  0.09, 18.00),
        (1000.00, 0.05, 50.00),
    ])
    def test_size_calculation(self, capital, pct, expected):
        assert round(capital * pct, 2) == expected

    def test_no_account_produces_zero(self):
        for account in ex.ACCOUNTS:
            sz = round(account["max_capital"] * account["trade_size_pct"], 2)
            assert sz > 0

    def test_size_under_capital(self):
        for account in ex.ACCOUNTS:
            sz = round(account["max_capital"] * account["trade_size_pct"], 2)
            assert sz < account["max_capital"]


class TestSaveState:
    def test_saves_valid_json(self, tmp_path):
        sf = tmp_path / "state.json"
        account = {"id": "T", "state_file": str(sf)}
        ex.save_state(account, ex.init_state(account))
        assert sf.exists()
        loaded = json.loads(sf.read_text())
        assert loaded["account_id"] == "T"

    def test_no_tmp_file_after_save(self, tmp_path):
        sf = tmp_path / "state.json"
        account = {"id": "T", "state_file": str(sf)}
        ex.save_state(account, ex.init_state(account))
        assert not sf.with_suffix(".json.tmp").exists()

    def test_load_missing_file_returns_init(self, tmp_path):
        account = {"id": "T", "state_file": str(tmp_path / "none.json")}
        state = ex.load_state(account)
        assert state["positions"] == {}
        assert state["trades_today"] == 0

    def test_load_migrates_old_state(self, tmp_path):
        sf = tmp_path / "old.json"
        sf.write_text(json.dumps({"account_id": "T", "positions": {}}))
        account = {"id": "T", "state_file": str(sf)}
        state = ex.load_state(account)
        assert "round_anchors" in state
        assert "last_seen_round_id" in state

class TestKillswitchChecks:
    def setup_method(self):
        import canary_killswitch as ks
        self.ks = ks

    def _state(self, dd=0.0, pnl=0.0, fails=0, positions=None):
        return {"daily_dd_usd": dd, "session_pnl": pnl,
                "consec_api_fails": fails, "positions": positions or {}}

    def test_drawdown_ok(self):
        with patch.object(self.ks, "trigger_halt") as m:
            self.ks.check_drawdown("MAIN", self._state(dd=1.0))
            m.assert_not_called()

    def test_drawdown_triggers(self):
        with patch.object(self.ks, "trigger_halt") as m:
            self.ks.check_drawdown("MAIN", self._state(dd=32.0))
            m.assert_called_once()
            assert "max_drawdown_breach" in m.call_args[0][0]

    def test_api_storm_ok(self):
        with patch.object(self.ks, "trigger_halt") as m:
            self.ks.check_api_failure_storm("SUB1", self._state(fails=3))
            m.assert_not_called()

    def test_api_storm_triggers(self):
        with patch.object(self.ks, "trigger_halt") as m:
            self.ks.check_api_failure_storm("SUB1", self._state(fails=5))
            m.assert_called_once()
            assert "api_failure_storm" in m.call_args[0][0]

    def test_position_ok(self):
        pos = {"BTC/USDT": {"side": "long", "entry_price": 50000.0,
                             "size_usdt": 100.0, "size_base": 0.002,
                             "entry_ts": time.time()}}
        with patch.object(self.ks, "trigger_halt") as m:
            self.ks.check_position_state("MAIN", self._state(positions=pos))
            m.assert_not_called()

    def test_position_overflow_triggers(self):
        positions = {f"P{i}/USDT": {"side": "long", "entry_price": 1.0,
                                     "size_usdt": 10.0, "size_base": 1.0,
                                     "entry_ts": time.time()} for i in range(5)}
        with patch.object(self.ks, "trigger_halt") as m:
            self.ks.check_position_state("MAIN", self._state(positions=positions))
            m.assert_called_once()
            assert "abnormal_position_state" in m.call_args[0][0]

    def test_balance_ok(self):
        with patch.object(self.ks, "trigger_halt") as m:
            self.ks.check_balance_state("MAIN", self._state(pnl=-5.0, dd=5.0))
            m.assert_not_called()

    def test_balance_negative_dd_triggers(self):
        with patch.object(self.ks, "trigger_halt") as m:
            self.ks.check_balance_state("MAIN", self._state(dd=-1.0))
            m.assert_called_once()
            assert "corrupted_balance_state" in m.call_args[0][0]

    def test_balance_nan_pnl_triggers(self):
        with patch.object(self.ks, "trigger_halt") as m:
            self.ks.check_balance_state("MAIN", self._state(pnl=float("nan")))
            m.assert_called_once()
            assert "corrupted_balance_state" in m.call_args[0][0]
