#!/usr/bin/env python3
"""
check_agents.py — preflight + smoke tests for the 3-account live battle.

Validates MAIN, SUB1, SUB2 agents without sending real orders:
  • Config consistency: canary_config.json ↔ canary_executor.ACCOUNTS
  • API key files: present, perms 0600, parseable
  • ccxt installed and Gate exchange instantiable
  • Authenticated balance fetch (read-only) per account
  • Balance ≤ balance_ceil per account
  • Live ticker fetch for all 4 pairs (BTC/ETH/XRP/SOL)
  • Pure-function tests with mock exchange (signal, scoring, state I/O)

Exit codes:
  0 — all checks passed
  1 — at least one check failed
  2 — usage / environment error

Usage:
  python3 canary/check_agents.py            # full check (needs live API keys)
  python3 canary/check_agents.py --offline  # skip exchange calls; logic tests only
  python3 canary/check_agents.py --account MAIN   # check single account
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CONFIG_FILE = HERE / "canary_config.json"
EXECUTOR_FILE = HERE / "canary_executor.py"

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("check")


class Check:
    """Tiny test harness — records pass/fail and prints a summary."""

    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.skipped: list[tuple[str, str]] = []

    def run(self, name: str, fn: Callable[[], Any]) -> None:
        try:
            fn()
        except SkipTest as e:
            self.skipped.append((name, str(e)))
            log.info("  SKIP  %s — %s", name, e)
        except AssertionError as e:
            self.failed.append((name, str(e) or "assertion failed"))
            log.info("  FAIL  %s — %s", name, e)
        except Exception as e:  # noqa: BLE001 - surface any failure
            self.failed.append((name, f"{type(e).__name__}: {e}"))
            log.info("  FAIL  %s — %s: %s", name, type(e).__name__, e)
        else:
            self.passed.append(name)
            log.info("  PASS  %s", name)

    def summary(self) -> int:
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        log.info("")
        log.info("=" * 60)
        log.info(
            "RESULT: %d/%d passed · %d failed · %d skipped",
            len(self.passed), total, len(self.failed), len(self.skipped),
        )
        if self.failed:
            log.info("Failures:")
            for name, msg in self.failed:
                log.info("  - %s: %s", name, msg)
        return 1 if self.failed else 0


class SkipTest(Exception):
    pass


def _import_executor():
    """Load canary_executor as a module without running main()."""
    spec = importlib.util.spec_from_file_location("canary_executor", EXECUTOR_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {EXECUTOR_FILE}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_config_consistency(check: Check, executor) -> None:
    """canary_config.json must agree with the executor's ACCOUNTS / pair list."""

    def _load_config():
        assert CONFIG_FILE.exists(), f"missing {CONFIG_FILE}"
        cfg = json.loads(CONFIG_FILE.read_text())
        assert "accounts" in cfg and "trading" in cfg, "config missing keys"

    check.run("config: file loadable", _load_config)

    cfg = json.loads(CONFIG_FILE.read_text())

    def _accounts_match():
        cfg_ids = sorted(cfg["accounts"].keys())
        exe_ids = sorted(a["id"] for a in executor.ACCOUNTS)
        assert cfg_ids == exe_ids, f"config={cfg_ids} executor={exe_ids}"
        assert cfg_ids == ["MAIN", "SUB1", "SUB2"], f"unexpected accounts: {cfg_ids}"

    check.run("config: 3 accounts (MAIN/SUB1/SUB2)", _accounts_match)

    def _capitals_match():
        for acc in executor.ACCOUNTS:
            c = cfg["accounts"][acc["id"]]
            assert abs(c["max_capital_usd"] - acc["max_capital"]) < 1e-6, \
                f"{acc['id']} capital mismatch: cfg={c['max_capital_usd']} exe={acc['max_capital']}"
            assert abs(c["balance_ceiling_usd"] - acc["balance_ceil"]) < 1e-6, \
                f"{acc['id']} ceiling mismatch"
            assert abs(c["trade_size_pct"] - acc["trade_size_pct"]) < 1e-9, \
                f"{acc['id']} trade_size mismatch"

    check.run("config: capital/ceiling/size match executor", _capitals_match)

    def _pairs_match():
        assert cfg["trading"]["pairs"] == executor.ALL_PAIRS, "pair list mismatch"

    check.run("config: pairs match executor", _pairs_match)

    def _capital_total():
        total = sum(c["max_capital_usd"] for c in cfg["accounts"].values())
        assert abs(total - cfg["total_capital_usd"]) < 1e-6, \
            f"sum={total} != total_capital_usd={cfg['total_capital_usd']}"

    check.run("config: per-account capitals sum to total_capital_usd", _capital_total)


def check_api_keys(check: Check, executor, accounts: list[dict]) -> None:
    """Each account needs a readable, well-formed, 0600-permissioned key file."""
    for acc in accounts:
        kf = Path(acc["api_key_file"])

        def _check(acc=acc, kf=kf) -> None:
            if not kf.exists():
                raise SkipTest(f"{kf} missing (not a deploy host)")
            perms = oct(kf.stat().st_mode)[-3:]
            assert perms == "600", f"{kf} perms {perms} not 600"
            parts = kf.read_text().strip().split(":")
            assert len(parts) == 2 and parts[0] and parts[1], f"{kf} malformed (need key:secret)"

        check.run(f"keyfile: {acc['id']} present, perms 600, parseable", _check)


def check_exchange_live(check: Check, executor, accounts: list[dict]) -> None:
    """Authenticated read-only Gate.io calls per account. Skipped if keys absent."""
    try:
        import ccxt  # noqa: F401
    except ImportError:
        check.run("ccxt: importable", lambda: (_ for _ in ()).throw(
            SkipTest("ccxt not installed — install on deploy host")))
        return

    check.run("ccxt: importable", lambda: None)

    for acc in accounts:
        kf = Path(acc["api_key_file"])

        def _bal(acc=acc, kf=kf) -> None:
            if not kf.exists():
                raise SkipTest(f"{kf} missing")
            ex = executor.make_ex(acc)
            bal = ex.fetch_balance()
            usdt = float(bal.get("USDT", {}).get("free", 0))
            assert usdt <= acc["balance_ceil"], \
                f"{acc['id']} balance ${usdt:.2f} > ceil ${acc['balance_ceil']}"
            log.info("      $%.2f USDT (ceil $%.2f)", usdt, acc["balance_ceil"])

        check.run(f"exchange: {acc['id']} auth + balance ≤ ceil", _bal)

    def _tickers() -> None:
        if not Path(accounts[0]["api_key_file"]).exists():
            raise SkipTest("no keys to fetch tickers")
        ex = executor.make_ex(accounts[0])
        for pair in executor.ALL_PAIRS:
            t = ex.fetch_ticker(pair)
            assert t.get("last") is not None, f"{pair} ticker has no 'last'"

    check.run(f"exchange: tickers fetch for {len(executor.ALL_PAIRS)} pairs", _tickers)


def check_state_io(check: Check, executor, accounts: list[dict]) -> None:
    """init_state → save_state → load_state round-trips with a tempdir."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for acc in accounts:
            ephemeral = dict(acc)
            ephemeral["state_file"] = td_path / f"state_{acc['id'].lower()}.json"

            def _roundtrip(ephemeral=ephemeral) -> None:
                s = executor.init_state(ephemeral)
                assert s["account_id"] == ephemeral["id"]
                assert s["trades_today"] == 0
                executor.save_state(ephemeral, s)
                s2 = executor.load_state(ephemeral)
                assert s2 == s, "state did not round-trip"

            check.run(f"state: {acc['id']} init/save/load round-trip", _roundtrip)


# ---- Mock exchange for offline / pure-logic tests --------------------------

class MockTicker(dict):
    pass


def _make_mock_exchange(prices: dict[str, float], daily_above_sma: bool = True):
    """Return a minimal ccxt-like exchange for offline signal / scoring tests."""

    class Mock:
        def fetch_ticker(self, pair: str) -> dict:
            return {
                "last": prices[pair],
                "percentage": 1.5,
                "quoteVolume": 1_000_000.0,
            }

        def fetch_ohlcv(self, pair: str, tf: str, limit: int = 80) -> list[list]:
            # craft candles whose closes sit above (or below) the would-be SMA
            base = prices[pair]
            if daily_above_sma:
                closes = [base * 0.9] * (limit - 1) + [base]
            else:
                closes = [base * 1.2] * (limit - 1) + [base]
            return [[0, 0, 0, 0, c, 0] for c in closes]

    return Mock()


def check_logic(check: Check, executor) -> None:
    """Pure-function tests for score_pairs / get_signal — no network."""
    prices = {"BTC/USDT": 60000, "ETH/USDT": 3000, "XRP/USDT": 0.5, "SOL/USDT": 150}

    def _score() -> None:
        ex = _make_mock_exchange(prices)
        ranked = executor.score_pairs(ex)
        assert sorted(ranked) == sorted(executor.ALL_PAIRS), \
            f"score_pairs lost pairs: {ranked}"

    check.run("logic: score_pairs returns all configured pairs", _score)

    def _signal_buy() -> None:
        ex = _make_mock_exchange(prices, daily_above_sma=True)
        sig = executor.get_signal(ex, "BTC/USDT")
        assert sig["signal"] == "BUY", f"expected BUY, got {sig}"
        assert sig["price"] == prices["BTC/USDT"]

    check.run("logic: get_signal=BUY when price above SMA", _signal_buy)

    def _signal_sell() -> None:
        ex = _make_mock_exchange(prices, daily_above_sma=False)
        sig = executor.get_signal(ex, "ETH/USDT")
        assert sig["signal"] == "SELL", f"expected SELL, got {sig}"

    check.run("logic: get_signal=SELL when price below SMA", _signal_sell)


def check_arm_file(check: Check) -> None:
    """The arm file is created on the deploy host — skipped if absent."""

    def _arm() -> None:
        if not executor.ARM_FILE.exists():
            raise SkipTest(f"{executor.ARM_FILE} missing (not a deploy host)")
        executor.check_arm()  # raises SystemExit on bad arm

    check.run("arm file: present and well-formed", _arm)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--offline", action="store_true", help="skip exchange / arm-file checks")
    p.add_argument("--account", choices=["MAIN", "SUB1", "SUB2"], help="restrict to one account")
    return p.parse_args()


def main() -> int:
    global executor  # used by check_arm_file
    args = parse_args()
    try:
        executor = _import_executor()
    except SystemExit as e:
        # canary_executor.fail_closed() calls sys.exit; import shouldn't trigger it
        log.error("Could not import canary_executor: %s", e)
        return 2
    except Exception as e:  # noqa: BLE001
        log.error("Could not import canary_executor: %s", e)
        return 2

    accounts = [a for a in executor.ACCOUNTS if not args.account or a["id"] == args.account]
    if not accounts:
        log.error("No matching account: %s", args.account)
        return 2

    check = Check()

    log.info("=== Config consistency ===")
    check_config_consistency(check, executor)

    log.info("\n=== API key files ===")
    check_api_keys(check, executor, accounts)

    log.info("\n=== State I/O ===")
    check_state_io(check, executor, accounts)

    log.info("\n=== Trading logic (mock exchange) ===")
    check_logic(check, executor)

    if not args.offline:
        log.info("\n=== Arm file ===")
        check_arm_file(check)

        log.info("\n=== Exchange (live read-only) ===")
        check_exchange_live(check, executor, accounts)
    else:
        log.info("\n=== Skipped: exchange + arm file (--offline) ===")

    return check.summary()


if __name__ == "__main__":
    sys.exit(main())
