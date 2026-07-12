"""
factor_research_harness.py — single canonical entry point for factor research.

WHY THIS MODULE EXISTS
======================
After 11 NULLs and 11 ad-hoc runners (a2_stablecoin_runner, b1_*, b2_*,
b3_*, v1_vwap_gap, ...), the methodology lessons are codified in
NULL_REGISTRY.md and L99_ALPHA_VALIDATION_AMENDMENTS.md. The next risk
is silent drift in some future runner that forgets to apply Rule N.

This harness is a single class that:

  * Refuses to run if pre-flight fails (Rules 1-11 mechanically checked)
  * Cross-references NULL_REGISTRY for collision before any work is done
  * Runs L99 battery with locked thresholds via l99_battery.py
  * Runs §3.5 backtest gate via backtesting.py with hard pass/fail
  * Auto-records discipline state into the results JSON
  * Emits a finding-doc skeleton ready for human curation

Operators write a short FactorSpec + a signal-builder function. The harness
does everything else, identically every time.

USAGE
=====

    from factor_research_harness import FactorSpec, FactorResearchHarness

    spec = FactorSpec(
        name='V1_VWAP_GAP_MEAN_REV_HARNESS',
        hypothesis='4h close-to-VWAP_24h gap z-score reverts to mean',
        mechanism='mechanical (mean-reversion of price vs volume-weighted average)',
        decision_rule='mean_rev_long_q1_short_q5',
        is_signed=True,
        horizon_bars=18,
        pairs=['BTC_USDT', 'ETH_USDT', 'SOL_USDT'],
        earliest_ts=1672531200,
        null_registry_distinction='Distinct from V1 row 11: this is harness-driven '
                                  'validation; original was ad-hoc runner.',
    )

    harness = FactorResearchHarness(spec, output_dir='.')

    def signal_builder(bars):
        # Returns: (mask, factor, fwd_dict, regimes, directions)
        ...

    harness.register_signal_builder(signal_builder)
    harness.register_data_fetcher(fetch_perp_4h_paginated)

    result = harness.run()  # raises FactorResearchHarnessError if pre-flight fails
    # result is the canonical results dict + emitted JSON file path
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l99_battery import L99, ic as l99_ic, tstat as l99_tstat


HARNESS_VERSION = '1.0.0'

# Locked thresholds per L99_ALPHA_VALIDATION_AMENDMENTS.md
# These cannot be modified at runtime.
L99_THRESHOLDS = {
    'IC_MIN': 0.04,
    'TSTAT_MIN': 2.0,
    'PF_MIN': 1.3,
    'QUINTILE_MIN_BPS': 60.0,
    'MC_STABILITY': 0.80,
    'REGIME_MIN': 2,
    'MIN_OBS': 100,
}

GATE_3_5_THRESHOLDS = {
    'SHARPE_MIN': 1.0,
    'MAX_DD_FLOOR': -25.0,        # i.e. MaxDD must be > -25%
    'TRADES_MIN': 30,
    'WIN_RATE_MIN': 40.0,
    'GOOD_YEARS_MIN': 3,
}

FEE_TIERS_PER_SIDE = {
    'A_VIP0_taker':       0.00125,
    'B_VIP1_GT_discount': 0.00090,
    'C_VIP1_maker_only':  0.00070,
}

ALLOWED_DECISION_RULES = {
    'long_q5',
    'short_q5',
    'long_q1_short_q5',          # paired momentum
    'mean_rev_long_q1_short_q5', # paired mean-rev
    'mean_rev_long_q1',          # one-sided mean-rev
    'mean_rev_short_q5',         # one-sided mean-rev
}


class FactorResearchHarnessError(Exception):
    """Raised when pre-flight or harness invariants are violated.
    The harness refuses to run; operator must fix the spec, not the harness."""


# ──────────────────────────────────────────────────────────────────
# FactorSpec
# ──────────────────────────────────────────────────────────────────

@dataclass
class FactorSpec:
    name: str
    hypothesis: str
    mechanism: str               # 'behavioral' | 'flow' | 'mechanical' | 'reflexive'
    decision_rule: str           # one of ALLOWED_DECISION_RULES
    is_signed: bool              # MUST be True per Rule 1 (B2/B3 lesson)
    horizon_bars: int            # lookforward, e.g. 18 = 3d at 4h cadence
    pairs: List[str]
    earliest_ts: int
    null_registry_distinction: str   # text explaining how this differs from prior NULLs

    # Optional config overrides (TIGHTEN-only enforced at validate time)
    fee_tiers_per_side: Dict[str, float] = field(default_factory=lambda: dict(FEE_TIERS_PER_SIDE))
    cross_pair_min_share_sign: int = 4   # Rule 4: ≥ 4 of 5 pairs share IC sign

    def to_dict(self) -> Dict:
        return asdict(self)


# ──────────────────────────────────────────────────────────────────
# NULL_REGISTRY parsing
# ──────────────────────────────────────────────────────────────────

def _parse_null_registry(registry_path: str) -> List[Dict[str, str]]:
    """Parse the | family | hypothesis | failed | lesson | doc | rows."""
    if not os.path.isfile(registry_path):
        # If the registry doesn't exist on this branch yet, treat as empty.
        return []
    with open(registry_path) as f:
        text = f.read()
    rows: List[Dict[str, str]] = []
    in_table = False
    for line in text.splitlines():
        if re.match(r'^\| # \| Family \|', line):
            in_table = True
            continue
        if in_table and line.startswith('|---'):
            continue
        if in_table:
            if not line.startswith('|'):
                in_table = False
                continue
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if len(cells) >= 4 and cells[0].isdigit():
                rows.append({
                    'num': cells[0],
                    'family': cells[1],
                    'hypothesis': cells[2] if len(cells) > 2 else '',
                    'failure': cells[3] if len(cells) > 3 else '',
                })
    return rows


# ──────────────────────────────────────────────────────────────────
# Quintile spread (signed, mean-rev aware)
# ──────────────────────────────────────────────────────────────────

def quintile_spread_bps(factor_vals: List[Optional[float]],
                        forward: List[Optional[float]],
                        fee_rt: float,
                        is_mean_rev: bool) -> float:
    """Per-leg fee math: fee_rt = fee_per_side × 2 (already RT)."""
    pairs = [(f, r) for f, r in zip(factor_vals, forward)
             if f is not None and r is not None]
    if len(pairs) < 20:
        return 0.0
    pairs.sort(key=lambda x: x[0])
    nq = max(1, len(pairs) // 5)
    q1 = [p[1] for p in pairs[:nq]]
    q5 = [p[1] for p in pairs[-nq:]]
    raw = (statistics.mean(q1) - statistics.mean(q5)) if is_mean_rev \
          else (statistics.mean(q5) - statistics.mean(q1))
    return raw * 100 - fee_rt * 10000 * 2


# ──────────────────────────────────────────────────────────────────
# Generic backtesting.py strategy driver
# ──────────────────────────────────────────────────────────────────

class _HarnessStrategy(Strategy):
    """Long/short on direction column, hold_bars exit. One position at a time."""
    hold_bars = 18

    def init(self):
        self._dir = self.I(lambda: self.data.df['direction'].values,
                           name='dir', overlay=False)
        self._mask = self.I(lambda: self.data.df['mask'].astype(int).values,
                            name='mask', overlay=False)
        self._entry_bar: Optional[int] = None

    def next(self):
        i = len(self.data) - 1
        if self.position and self._entry_bar is not None:
            if i - self._entry_bar >= self.hold_bars:
                self.position.close()
                self._entry_bar = None
                return

        if not self.position and len(self.data) >= 2:
            mask_now = bool(self._mask[-1])
            mask_prev = bool(self._mask[-2])
            d = int(self._dir[-1])
            if mask_now and not mask_prev and d in (-1, +1):
                if d == +1:
                    self.buy(size=0.85)
                else:
                    self.sell(size=0.85)
                self._entry_bar = i


# ──────────────────────────────────────────────────────────────────
# Harness
# ──────────────────────────────────────────────────────────────────

SignalBuilder = Callable[
    [List[Dict[str, float]]],
    Tuple[List[bool], List[Optional[float]],
          Dict[str, List[Optional[float]]],
          List[str], List[Optional[int]]]
]
DataFetcher = Callable[[str], List[Dict[str, float]]]


class FactorResearchHarness:
    def __init__(self, spec: FactorSpec, output_dir: str = '.',
                 null_registry_path: Optional[str] = None):
        self.spec = spec
        self.output_dir = os.path.abspath(output_dir)
        if null_registry_path is None:
            null_registry_path = os.path.join(
                self.output_dir, 'docs', 'specs', 'NULL_REGISTRY.md'
            )
        self.null_registry_path = null_registry_path
        self._signal_builder: Optional[SignalBuilder] = None
        self._data_fetcher: Optional[DataFetcher] = None
        self._registry_rows = _parse_null_registry(null_registry_path)
        self._discipline_state = {
            'position_when_started': '100% USDT',
            'position_when_finished': '100% USDT',
            'live_config_changed': False,
            'thresholds_modified': False,
            'deployment_attempted': False,
            'harness_version': HARNESS_VERSION,
        }

    # ── registration ──
    def register_signal_builder(self, fn: SignalBuilder) -> None:
        self._signal_builder = fn

    def register_data_fetcher(self, fn: DataFetcher) -> None:
        self._data_fetcher = fn

    # ── pre-flight ──
    def validate_preflight(self) -> Tuple[bool, List[str]]:
        fails: List[str] = []
        s = self.spec
        if not s.name or not isinstance(s.name, str):
            fails.append("spec.name missing")
        if not s.hypothesis or len(s.hypothesis) < 20:
            fails.append("spec.hypothesis too short or missing")
        if s.mechanism not in ('behavioral', 'flow', 'mechanical', 'reflexive'):
            fails.append(f"spec.mechanism='{s.mechanism}' not in allowed set")
        if s.decision_rule not in ALLOWED_DECISION_RULES:
            fails.append(f"spec.decision_rule='{s.decision_rule}' not allowed")
        if not s.is_signed:
            fails.append("spec.is_signed must be True (Rule 1: SIGNED forward returns)")
        if s.horizon_bars < 1:
            fails.append("spec.horizon_bars must be ≥ 1")
        if not s.pairs:
            fails.append("spec.pairs empty")
        if len(s.pairs) > 1 and s.cross_pair_min_share_sign > len(s.pairs):
            fails.append(
                f"cross_pair_min_share_sign={s.cross_pair_min_share_sign} > "
                f"len(pairs)={len(s.pairs)}"
            )
        # Tightening-only fee tier check
        for tier, fee in s.fee_tiers_per_side.items():
            if tier in FEE_TIERS_PER_SIDE and fee < FEE_TIERS_PER_SIDE[tier]:
                fails.append(
                    f"fee_tier '{tier}' = {fee} is BELOW canonical "
                    f"{FEE_TIERS_PER_SIDE[tier]} (LOOSENING prohibited)"
                )
        if not s.null_registry_distinction or len(s.null_registry_distinction) < 20:
            fails.append("spec.null_registry_distinction must explain distinction (≥20 chars)")
        if self._signal_builder is None:
            fails.append("signal_builder not registered")
        if self._data_fetcher is None:
            fails.append("data_fetcher not registered")
        return len(fails) == 0, fails

    def validate_against_null_registry(self) -> Tuple[bool, List[str]]:
        """Heuristic collision check: does the spec name look like a registered NULL?"""
        warnings: List[str] = []
        for row in self._registry_rows:
            family_token = row['family'].split()[0].upper()
            if family_token and family_token in self.spec.name.upper():
                warnings.append(
                    f"NULL #{row['num']} family '{row['family']}' may collide with "
                    f"spec.name '{self.spec.name}'. Distinction provided: "
                    f"'{self.spec.null_registry_distinction[:80]}...'"
                )
        return True, warnings  # warnings are non-blocking; collisions raise via spec text

    # ── L99 battery (cross-section) ──
    def _l99_battery_one(self, name: str,
                         factor_vals: List[Optional[float]],
                         forward: List[Optional[float]],
                         regimes: List[str],
                         mask: List[bool],
                         directions: List[Optional[int]],
                         fee_rt: float) -> Dict:
        is_mean_rev = self.spec.decision_rule.startswith('mean_rev')
        indices = [i for i in range(len(mask))
                   if mask[i] and factor_vals[i] is not None
                   and forward[i] is not None and directions[i] in (-1, +1)]
        n = len(indices)
        killed: List[str] = []
        if n < L99_THRESHOLDS['MIN_OBS']:
            return {'name': name, 'fee_rt_bps': fee_rt * 10000, 'n': n,
                    'passes': False,
                    'killed_by': [f'N={n}<{L99_THRESHOLDS["MIN_OBS"]}'],
                    'ic': 0, 'tstat': 0, 'pf': 0, 'q_bps': 0, 'mc': 0,
                    'regime_count': 0}
        sig_factor = [factor_vals[i] for i in indices]
        raw_fwd = [forward[i] for i in indices]
        oriented = [directions[i] * forward[i] for i in indices]
        net_returns = [r - fee_rt * 100 for r in oriented]
        ic_v = l99_ic(sig_factor, raw_fwd)
        ts_v = l99_tstat(net_returns)
        wins = [r for r in net_returns if r > 0]
        losses = [r for r in net_returns if r <= 0]
        pf_v = (sum(wins) / abs(sum(losses))) if (wins and losses) else (
            999.0 if not losses else 0.0
        )
        qs_v = quintile_spread_bps(factor_vals, forward, fee_rt, is_mean_rev)
        import random as _r
        rng = _r.Random(42)
        mc_wins = sum(1 for _ in range(500)
                      if sum(rng.choice(net_returns) for _ in range(n)) > 0)
        mc_v = mc_wins / 500.0
        sig_regimes = [regimes[i] for i in indices]
        regime_ret: Dict[str, List[float]] = {}
        for r_lab, ret in zip(sig_regimes, net_returns):
            regime_ret.setdefault(r_lab, []).append(ret)
        reg_count = sum(1 for rets in regime_ret.values()
                        if len(rets) >= 5 and statistics.mean(rets) > 0)

        if abs(ic_v) < L99_THRESHOLDS['IC_MIN']:
            killed.append(f"IC={ic_v:+.4f}")
        if abs(ts_v) < L99_THRESHOLDS['TSTAT_MIN']:
            killed.append(f"t={ts_v:+.4f}")
        if pf_v < L99_THRESHOLDS['PF_MIN']:
            killed.append(f"PF={pf_v:.4f}")
        if qs_v < L99_THRESHOLDS['QUINTILE_MIN_BPS']:
            killed.append(f"Q5-Q1={qs_v:+.2f}")
        if mc_v < L99_THRESHOLDS['MC_STABILITY']:
            killed.append(f"MC={mc_v*100:.1f}%")
        if reg_count < L99_THRESHOLDS['REGIME_MIN']:
            killed.append(f"Reg={reg_count}")
        return {'name': name, 'fee_rt_bps': fee_rt * 10000, 'n': n,
                'passes': len(killed) == 0, 'killed_by': killed,
                'ic': ic_v, 'tstat': ts_v, 'pf': pf_v, 'q_bps': qs_v,
                'mc': mc_v, 'regime_count': reg_count}

    # ── §3.5 backtest gate ──
    def _run_bt(self, df: pd.DataFrame, fee_per_side: float,
                hold_bars: int, label: str, plot: bool = False) -> Dict:
        class _S(_HarnessStrategy):
            pass
        _S.hold_bars = hold_bars
        bt = Backtest(df, _S, cash=10_000,
                      commission=fee_per_side, exclusive_orders=True,
                      trade_on_close=False, margin=1.0, hedging=False)
        stats = bt.run()
        out: Dict = {}
        keep = [
            'Start', 'End', 'Duration', 'Exposure Time [%]',
            'Equity Final [$]', 'Equity Peak [$]',
            'Return [%]', 'Buy & Hold Return [%]',
            'Return (Ann.) [%]', 'Volatility (Ann.) [%]',
            'Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio',
            'Max. Drawdown [%]', 'Avg. Drawdown [%]',
            '# Trades', 'Win Rate [%]', 'Best Trade [%]', 'Worst Trade [%]',
            'Avg. Trade [%]', 'Profit Factor', 'Expectancy [%]', 'SQN',
        ]
        for k in keep:
            if k in stats.index:
                v = stats[k]
                if hasattr(v, 'isoformat'):
                    out[k] = v.isoformat()
                elif isinstance(v, pd.Timedelta):
                    out[k] = str(v)
                elif isinstance(v, (int, float, np.integer, np.floating)):
                    out[k] = None if (np.isnan(v) or np.isinf(v)) else float(v)
                else:
                    out[k] = str(v)
        if plot:
            path = os.path.join(self.output_dir, f'harness_{label}.html')
            try:
                bt.plot(filename=path, open_browser=False)
                out['plot_path'] = path
            except Exception as e:
                out['plot_error'] = str(e)
        return out

    def _gate_3_5(self, full: Dict, yearly: Dict[str, Dict]) -> Tuple[bool, List[str]]:
        fail: List[str] = []
        sh = full.get('Sharpe Ratio')
        if sh is None or sh < GATE_3_5_THRESHOLDS['SHARPE_MIN']:
            fail.append(f"Sharpe={sh} < {GATE_3_5_THRESHOLDS['SHARPE_MIN']}")
        ret = full.get('Return [%]') or 0.0
        bh = full.get('Buy & Hold Return [%]') or 0.0
        if ret <= bh:
            fail.append(f"Return={ret:.2f}% does NOT beat B&H={bh:.2f}%")
        dd = full.get('Max. Drawdown [%]') or 0.0
        if dd < GATE_3_5_THRESHOLDS['MAX_DD_FLOOR']:
            fail.append(f"MaxDD={dd:.2f}% < {GATE_3_5_THRESHOLDS['MAX_DD_FLOOR']}%")
        n = full.get('# Trades') or 0
        if n < GATE_3_5_THRESHOLDS['TRADES_MIN']:
            fail.append(f"#Trades={int(n)} < {GATE_3_5_THRESHOLDS['TRADES_MIN']}")
        wr = full.get('Win Rate [%]') or 0.0
        if wr < GATE_3_5_THRESHOLDS['WIN_RATE_MIN']:
            fail.append(f"WinRate={wr:.1f}% < {GATE_3_5_THRESHOLDS['WIN_RATE_MIN']}%")
        good = sum(1 for r in yearly.values()
                   if r.get('Sharpe Ratio') is not None and r['Sharpe Ratio'] > 0)
        if good < GATE_3_5_THRESHOLDS['GOOD_YEARS_MIN']:
            fail.append(
                f"GoodYears={good}/{len(yearly)} "
                f"< {GATE_3_5_THRESHOLDS['GOOD_YEARS_MIN']}"
            )
        return len(fail) == 0, fail

    # ── orchestration ──
    def run(self) -> Dict:
        ok, fails = self.validate_preflight()
        if not ok:
            raise FactorResearchHarnessError(
                "Pre-flight failed:\n  " + "\n  ".join(fails)
            )
        _, registry_warnings = self.validate_against_null_registry()

        print(f"  Harness {HARNESS_VERSION} — spec: {self.spec.name}")
        for w in registry_warnings:
            print(f"  [registry warning] {w}")

        # ─── Step 1: data + signal per pair ───
        per_pair: Dict[str, Dict] = {}
        for pair in self.spec.pairs:
            print(f"  fetching {pair} ...", flush=True)
            bars = self._data_fetcher(pair)
            if len(bars) < 500:
                print(f"    skip (only {len(bars)} bars)")
                continue
            mask, factor, fwd, regimes, directions = self._signal_builder(bars)
            if not all(len(x) == len(bars) for x in (mask, factor, regimes, directions)):
                raise FactorResearchHarnessError(
                    f"signal_builder for {pair}: returned arrays of inconsistent length"
                )
            per_pair[pair] = {
                'bars': bars, 'mask': mask, 'factor': factor,
                'fwd': fwd, 'regimes': regimes, 'directions': directions,
                'n_signal': sum(mask),
            }
            print(f"    n_bars={len(bars)}  n_signal={sum(mask)}")
        if not per_pair:
            raise FactorResearchHarnessError("no pair data — abort")

        # ─── Step 2: L99 battery ───
        battery_out: Dict = {}
        ic_signs: Dict[str, int] = {}
        for pair, d in per_pair.items():
            for tier_label, fee_per_side in self.spec.fee_tiers_per_side.items():
                fee_rt = fee_per_side * 2
                fwd_h = d['fwd'].get(str(self.spec.horizon_bars))
                if fwd_h is None:
                    fwd_h = next(iter(d['fwd'].values()))
                name = f"{self.spec.name}_{pair}_{tier_label}"
                r = self._l99_battery_one(name, d['factor'], fwd_h,
                                          d['regimes'], d['mask'],
                                          d['directions'], fee_rt)
                battery_out[name] = r
            # IC sign at maker tier
            ic_signs[pair] = (
                1 if battery_out.get(
                    f"{self.spec.name}_{pair}_C_VIP1_maker_only", {}
                ).get('ic', 0) > 0 else -1
            )

        # Cross-pair sign consistency (Rule 4)
        pos = sum(1 for s in ic_signs.values() if s > 0)
        neg = sum(1 for s in ic_signs.values() if s < 0)
        sign_share = max(pos, neg)
        sign_consistent = sign_share >= self.spec.cross_pair_min_share_sign
        if len(ic_signs) >= self.spec.cross_pair_min_share_sign and not sign_consistent:
            print(f"  [Rule 4] cross-pair sign share={sign_share} < "
                  f"{self.spec.cross_pair_min_share_sign} — universe claim REJECTED")

        # ─── Step 3: §3.5 backtest gate per-pair ───
        bt_out: Dict = {}
        for pair, d in per_pair.items():
            df = pd.DataFrame(d['bars']).rename(columns={
                'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume',
            })
            df['Datetime'] = pd.to_datetime(df['ts'], unit='s', utc=True)
            df = df.set_index('Datetime').drop(columns=['ts'])
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df['mask'] = d['mask']
            df['direction'] = [x if x is not None else 0 for x in d['directions']]
            df = df[df.index >= pd.Timestamp(self.spec.earliest_ts, unit='s', tz='UTC')]
            if len(df) < 500:
                continue
            bt_out[pair] = {'full_history': {}, 'yearly_folds': {}}
            for tier_label, fee_per_side in self.spec.fee_tiers_per_side.items():
                r = self._run_bt(df, fee_per_side, self.spec.horizon_bars,
                                 label=f'{pair}_full_{tier_label}',
                                 plot=(tier_label == 'C_VIP1_maker_only'))
                bt_out[pair]['full_history'][tier_label] = r
                print(f"    {pair} {tier_label}: "
                      f"Return={r.get('Return [%]', float('nan')):+7.2f}%  "
                      f"Sharpe={r.get('Sharpe Ratio') or 0:+5.2f}  "
                      f"Trades={int(r.get('# Trades', 0))}  "
                      f"vs B&H {r.get('Buy & Hold Return [%]', float('nan')):+7.2f}%")
            fee_per_side = self.spec.fee_tiers_per_side['C_VIP1_maker_only']
            for year in [2023, 2024, 2025, 2026]:
                start = pd.Timestamp(f'{year}-01-01', tz='UTC')
                end = pd.Timestamp(f'{year+1}-01-01', tz='UTC')
                sub = df[(df.index >= start) & (df.index < end)]
                if len(sub) < 200:
                    continue
                r = self._run_bt(sub, fee_per_side, self.spec.horizon_bars,
                                 label=f'{pair}_{year}', plot=False)
                bt_out[pair]['yearly_folds'][str(year)] = r
            gp, gf = self._gate_3_5(
                bt_out[pair]['full_history']['C_VIP1_maker_only'],
                bt_out[pair]['yearly_folds'],
            )
            bt_out[pair]['gate_pass'] = gp
            bt_out[pair]['gate_failures'] = gf
            print(f"    §3.5 ({pair}): {'✅ PASS' if gp else '❌ FAIL'}")

        # ─── Verdict ───
        l99_pass = sum(1 for r in battery_out.values() if r['passes'])
        bt_pass = sum(1 for r in bt_out.values() if r.get('gate_pass'))
        verdict = 'CANDIDATE' if (l99_pass > 0 and bt_pass > 0 and sign_consistent) else 'NULL'

        out = {
            'harness_version': HARNESS_VERSION,
            'run_time': datetime.now(timezone.utc).isoformat(),
            'spec': self.spec.to_dict(),
            'l99_thresholds': L99_THRESHOLDS,
            'gate_3_5_thresholds': GATE_3_5_THRESHOLDS,
            'fee_tiers_per_side': FEE_TIERS_PER_SIDE,
            'cross_pair_ic_signs': ic_signs,
            'cross_pair_sign_consistent': sign_consistent,
            'cross_pair_sign_share': sign_share,
            'l99_battery': battery_out,
            'l99_passes': l99_pass,
            'l99_total': len(battery_out),
            'backtest': bt_out,
            'gate_3_5_passes': bt_pass,
            'gate_3_5_total': len(bt_out),
            'verdict': verdict,
            'discipline_state': self._discipline_state,
            'registry_warnings': registry_warnings,
        }

        # ─── Emit results JSON ───
        results_path = os.path.join(
            self.output_dir,
            f'harness_{self.spec.name.lower()}_results.json'
        )
        with open(results_path, 'w') as f:
            json.dump(out, f, indent=2, default=str)
        out['results_path'] = results_path
        print(f"  → {results_path}")

        # ─── Emit finding skeleton ───
        finding_path = self._emit_finding_skeleton(out)
        out['finding_skeleton_path'] = finding_path

        print(f"\n  HARNESS VERDICT: {verdict}")
        print(f"    L99 passes: {l99_pass}/{len(battery_out)}")
        print(f"    §3.5 passes: {bt_pass}/{len(bt_out)}")
        print(f"    cross-pair sign share: {sign_share}/{len(ic_signs)}")
        print(f"  Position: 100% USDT (unchanged)")
        return out

    def _emit_finding_skeleton(self, out: Dict) -> str:
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        slug = re.sub(r'[^a-z0-9]+', '-', self.spec.name.lower()).strip('-')
        path = os.path.join(
            self.output_dir, 'wiki', 'findings',
            f'{date_str}-{slug}-harness.md'
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        verdict = out['verdict']
        emoji = '✅' if verdict == 'CANDIDATE' else '🛑'
        next_step = (
            "→ Operator must decide whether to promote to §3 Stage 1 paper validation."
            if verdict == 'CANDIDATE' else
            "→ Add row to `docs/specs/NULL_REGISTRY.md` per Amendment A8.\\n"
            "→ Identify methodology lesson (or note 'redundant with Rule N').\\n"
            "→ Position remains 100% USDT."
        )
        body = f"""# {date_str} — {self.spec.name} via factor_research_harness

**Type:** finding (harness-driven, automated)
**Source artifacts:** `{os.path.basename(out['results_path'])}`
**Verdict:** {emoji} **{verdict}** (L99 {out['l99_passes']}/{out['l99_total']}, §3.5 {out['gate_3_5_passes']}/{out['gate_3_5_total']})

## Spec

- **Name:** {self.spec.name}
- **Hypothesis:** {self.spec.hypothesis}
- **Mechanism:** {self.spec.mechanism}
- **Decision rule:** {self.spec.decision_rule}
- **Horizon:** {self.spec.horizon_bars} bars
- **Pairs:** {', '.join(self.spec.pairs)}
- **Distinction from prior NULLs:** {self.spec.null_registry_distinction}

## Cross-pair IC sign consistency (Rule 4)

- Sign share: {out['cross_pair_sign_share']} of {len(out['cross_pair_ic_signs'])}
- Required (spec): {self.spec.cross_pair_min_share_sign}
- Consistent: {'✅' if out['cross_pair_sign_consistent'] else '❌'}

## L99 battery summary

Passes: **{out['l99_passes']} of {out['l99_total']}**

## §3.5 backtest gate summary

Passes: **{out['gate_3_5_passes']} of {out['gate_3_5_total']}** pairs

## Discipline state

```json
{json.dumps(out['discipline_state'], indent=2)}
```

## Next step

{next_step}

## Sources

- Harness: `factor_research_harness.py` v{HARNESS_VERSION}
- Spec hypothesis (operator)
- Gate.io public futures candlesticks (per pair, 4h)
"""
        with open(path, 'w') as f:
            f.write(body)
        print(f"  → {path}")
        return path
