"""
Pytest wrapper around the engine's internal invariants.
Mirrors the run.py --dryrun checks but expressed as discrete tests.
"""
import os, sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gods_level_engine import (
    C, Sig, Vote, T, Exchange, ALL_AGENTS, Consensus,
    PairScorer, TM
)


@pytest.fixture
def ex(): return Exchange()

@pytest.fixture
def bars(ex): return ex.sim_bars("BTC_USDT", 200, 99)

@pytest.fixture
def bull_bars(ex): return ex.sim_bars("BTC_USDT", 200, 42)


# ── Data & indicators ─────────────────────────────────────────
def test_bars_produced(bars):
    assert len(bars) == 200
    assert all(b.h >= b.l for b in bars)

def test_seed_variation(ex):
    a = ex.sim_bars("BTC_USDT", 200, 100)
    b = ex.sim_bars("BTC_USDT", 200, 200)
    assert a[-1].c != b[-1].c

def test_indicators(bars):
    cl = T.closes(bars)
    bb = T.bb(cl, 20, 2.0)
    assert T.last(T.ema(cl, 9)) > 0
    assert 0 < T.last(T.rsi(cl, 7)) < 100
    assert T.last(T.atr(bars, 14)) > 0
    assert T.last(bb["u"]) > T.last(bb["m"]) > T.last(bb["l"])


# ── Pair scoring ──────────────────────────────────────────────
def test_scorer_ranks_all_pairs(ex):
    scorer = PairScorer(ex)
    all_bars = {p: ex.sim_bars(p, 200, abs(hash(p))%9999) for p in C.PAIRS}
    ranks = [scorer.score(p, all_bars[p]) for p in C.PAIRS]
    assert len(ranks) == len(C.PAIRS)

def test_scorer_exclusion(ex):
    scorer = PairScorer(ex)
    all_bars = {p: ex.sim_bars(p, 200, abs(hash(p))%9999) for p in C.PAIRS}
    top = scorer.best(all_bars)
    excl = scorer.best({p:b for p,b in all_bars.items() if p != top.pair})
    assert excl.pair != top.pair


# ── Agents & consensus ────────────────────────────────────────
def test_agents_run_without_error(bars):
    for A in ALL_AGENTS:
        v = A().run(bars)
        assert isinstance(v, Vote)
        assert v.signal in (Sig.BUY, Sig.STRONG_BUY, Sig.HOLD)
        assert 0 <= v.conf <= 1

def test_consensus_requires_min_votes(bars):
    agents = [A() for A in ALL_AGENTS]
    votes = [ag.run(bars) for ag in agents]
    old = C.MIN_VOTES
    C.MIN_VOTES = 99
    try:
        assert Consensus().decide(votes) is None
    finally:
        C.MIN_VOTES = old


# ── Trade lifecycle ───────────────────────────────────────────
def _sample_vote(bars):
    b = bars[-1]
    atr5 = T.last(T.atr(bars, 7)) or b.c * 0.004
    return Vote("T", Sig.BUY, 0.75, b.c - atr5*0.35, b.c + atr5*1.8, "test")

def test_open_trade_ordered_levels(ex, bars):
    tm = TM(ex)
    t = tm.open("BTC_USDT", _sample_vote(bars), 80.0)
    assert t is not None
    assert t.stop < t.entry < t.tp1 < t.tp2 < t.tp3

def test_double_open_blocked(ex, bars):
    tm = TM(ex)
    tm.open("BTC_USDT", _sample_vote(bars), 80.0)
    assert tm.open("BTC_USDT", _sample_vote(bars), 50.0) is None

def test_tp3_exits_to_usdt(ex, bars):
    tm = TM(ex)
    t = tm.open("BTC_USDT", _sample_vote(bars), 80.0)
    reason = tm.update(t.tp3 * 1.001)
    assert reason == "TP3_EXIT"
    tm.close(t.tp3 * 1.001, reason)
    assert tm.open_t is None
    assert tm.history[-1].pnl > 0

def test_stop_loss_exits_to_usdt(ex, bars):
    tm = TM(ex)
    t = tm.open("BTC_USDT", _sample_vote(bars), 60.0)
    reason = tm.update(t.stop * 0.999)
    assert reason == "STOP_LOSS"
    tm.close(t.stop * 0.999, reason)
    assert tm.open_t is None
    assert tm.history[-1].pnl < 0

def test_time_stop(ex, bars):
    tm = TM(ex)
    t = tm.open("BTC_USDT", _sample_vote(bars), 50.0)
    t.t_open -= (C.MAX_HOLD_SEC + 5)
    assert tm.update(t.entry * 1.0001) == "TIME_STOP"

def test_emergency_stop(ex, bars):
    tm = TM(ex)
    b = bars[-1]
    v = Vote("E", Sig.BUY, 0.5, b.c*0.97, b.c*1.03, "emergency")
    t = tm.open("BTC_USDT", v, 100.0)
    assert tm.update(t.entry * 0.984) == "EMERGENCY_STOP"
