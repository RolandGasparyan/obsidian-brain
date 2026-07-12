# D6 Dry-Run Status — 2026-04-25

**Run by:** `microstructure_analyze.py` + `microstructure_robust_check.py`
**Data:** `/var/log/microstructure/` · 5 pairs × 1Hz × 15.7 hours (Apr 24–25)
**Status:** Pipeline VALIDATED · Preliminary signal STRONG · Final D6 still on Apr 30

---

## Why this dry-run was run early

ADR-001 schedules the D6 microstructure decision point for Apr 30 (5
days of WS data). This dry-run was executed at the partial-data mark
(15.7 h, ~13% of the planned window) for two reasons:

1. **Pipeline correctness:** any schema bug, missing column, or
   merge-asof error caught NOW gives 5 days to fix; caught on Apr 30
   blows up the only Phase A decision point.
2. **Early signal direction:** if features are clearly null, we can
   start ADR-002 B1 fallback prep ahead of schedule. If features are
   strongly significant, we know to plan the Phase B ensemble work.

Neither outcome is a deploy trigger — the final D6 verdict still
requires the full 5-day window for proper stationarity assessment.

---

## Pipeline result: ✅ Clean

| Check | Result |
|---|---|
| Parquet files load across all 5 pairs | ✅ |
| Schema columns present (`ts_ms`, `mid`, all 11 features) | ✅ |
| Forward returns computed for {60, 120, 300, 600, 1800}s | ✅ |
| `regime_label` populated (DEAD/NEUTRAL/EXPANSION/HIGH_IMPULSE) | ✅ |
| IC + t-stat math returns finite values | ✅ |
| No NaN propagation issues | ✅ |
| Per-day groupby works for stationarity | ✅ |
| BH-FDR multi-comparison runs without scipy import errors | ✅ |

No bugs found. Pipeline ready for the Apr 30 full run.

---

## Preliminary signal: 89 / 275 hypotheses survive triple-filter

**Triple-filter chain:**

| Stage | Survivors |
|---|---:|
| 0 — All hypotheses tested | 275 |
| 1 — Base gate (\|IC\| ≥ 0.04 AND \|t\| ≥ 2.0) | 146 |
| 2 — Stationarity (sign consistent across days) | 108 |
| 3 — Walk-forward (train 60% → test 40% same sign + ≥ 50% magnitude) | 89 |
| 4 — Benjamini-Hochberg FDR @ α=0.10 | 235 |
| **Triple-filter intersection (1 ∩ 2 ∩ 3 ∩ 4)** | **89** |

### Robust patterns hitting ≥ 3 pairs

| Feature | Strongest horizons | Pairs | Notes |
|---|---|---|---|
| `spread_pct` | 60s–1800s | **4/5** | BTC/ETH/SOL/XRP — strongest signal |
| `basis_pct` | 60–600s | 3/5 | BTC/ETH/XRP — perp-spot basis |
| `depth_imbalance` | 60–300s | 3–4/5 | top-of-book imbalance |
| `book_slope_bid/ask` | 60–600s | 3/5 | absorption capacity |
| `funding_rate_8h` | 300–1800s | 3/5 | sol/avax/btc — slow positioning |
| `ofi_30s` (Cont-Kukanov-Stoikov) | 60s | **2/5** | dropped from 5/5 in base — less robust |

### Top 8 individual cells (full IC / train IC / test IC)

| Pair | Feature | Horizon | Full IC | Train IC | Test IC |
|---|---|---:|---:|---:|---:|
| XRP_USDT | spread_pct | 1800s | +0.472 | +0.587 | +0.375 |
| ETH_USDT | spread_pct | 1800s | +0.406 | +0.441 | +0.453 |
| XRP_USDT | basis_pct | 120s | +0.379 | +0.381 | +0.391 |
| XRP_USDT | basis_pct | 60s | +0.367 | +0.374 | +0.374 |
| BTC_USDT | spread_pct | 1800s | +0.362 | +0.504 | +0.479 |
| SOL_USDT | funding_rate_8h | 1800s | +0.320 | +0.292 | +0.603 |
| AVAX_USDT | funding_rate_8h | 1800s | −0.294 | −0.320 | −0.221 |
| XRP_USDT | book_slope_bid | 300s | −0.286 | −0.243 | −0.357 |

These are the kind of magnitudes you'd want for a real
microstructure-based system. Some are suspiciously high and need
sanity checking — see "Caveats" below.

---

## Look-ahead audit (2026-04-25, post-dry-run)

A direct audit of `microstructure_collector.py` and the
`forward_returns()` lookup in `microstructure_analyze.py` was run
because `spread_pct` IC > 0.4 was suspiciously strong. Findings:

- **Collector — clean.** `now_ms = int(time.time() * 1000)` is captured
  at the start of each snapshot iteration. All features (`mid`,
  `spread_pct`, `book_slope_*`, `ofi_30s`, `delta_30s`, `basis_pct`,
  etc.) read `st.book` / `st.tape` / `st.deriv` state that was last
  updated by the WS handler at `last_update_ms ≤ now_ms`. The features
  are timestamped `now_ms` but reflect data from `[now_ms - book_lag,
  now_ms]`. Direction is conservative (slightly stale), opposite of
  look-ahead. `book_lag_ms` and `deriv_lag_ms` are written into every
  row for downstream auditing.

- **Analyzer — minor issue, fixed.** `forward_returns()` used
  `merge_asof(direction="nearest", tolerance=2)` to look up the future
  mid at `ts+T`. With `nearest`, the match could be up to 2s BEFORE
  `ts+T`. Effect: 0.11% timing slack at H=1800s, 3.3% at H=60s.
  Switched to `direction="forward"` so all forward returns are
  strictly at-or-after `ts+T`. Same fix applied to
  `microstructure_robust_check.py`.

- **Δ before/after fix on the partial dataset:**

  | Stage | Before | After | Δ |
  |---|---:|---:|---:|
  | Base hits | 146 | 144 | −2 |
  | Stationary | 108 | 105 | −3 |
  | Walk-forward stable | 89 | 89 | 0 |
  | BH-FDR | 235 | 233 | −2 |
  | Triple-filter survivors | 89 | 89 | 0 |

  Top IC magnitudes shifted by < 1% (XRP spread_pct@1800s: +0.472 →
  +0.475, ETH +0.406 → +0.400). The signal is robust to the
  correction. `D6_DRYRUN_ROBUST_V2.txt` records the post-fix output.

- **Verdict:** the +0.47 spread_pct IC is NOT a look-ahead artifact.
  Remaining suspicions (autocorrelation, regime co-movement) require
  bootstrap testing (queued for Apr 30 final run).

## Caveats — why this is NOT a deploy trigger

1. **Only 15.7 h of data.** The stationarity test only checks "sign
   consistent across 2 days." Real test on Apr 30 has 5 days of
   independent buckets.

2. **`spread_pct` IC > 0.4 is suspiciously strong.** Possible
   explanations:
   - **Real:** narrow spread predicts reversion, wide spread predicts
     directional. This is consistent with literature.
   - **Auto-correlation artifact:** `spread_pct` is highly persistent
     (its own value 30 min ago strongly predicts its current value),
     and forward log-return `fwd_ret_1800s` may share noise structure
     with concurrent spread realizations.
   - **Look-ahead bias:** if `spread_pct` is computed on a sample at
     time T but T's L2 snapshot was actually captured at T+ε due to
     queue-time, the feature includes information from the "future."
     Need to verify collector's snapshot time handling.

3. **High t-stats are partly N-driven.** With 36k samples, even
   |IC|=0.04 yields t≈7.6. The threshold |t|≥2.0 is essentially
   automatic; the |IC|≥0.04 floor is the real filter. We need to
   inspect t-stat under bootstrap, not just analytic.

4. **No volatility-adjustment.** Forward returns scale with realized
   vol; same |IC| during high-vol regime is more informative than
   during low-vol regime. The current analyzer does NOT vol-adjust.

5. **OFI dropped from strong (5/5) to weak (2/5)** under the triple
   filter. The classic Cont-Kukanov-Stoikov OFI signal is the most
   peer-reviewed feature in this stack. Its drop suggests our 30s
   window may be too short or too long for the regime we're collecting.

---

## 6-filter battery added (2026-04-25, post-audit)

The original triple-filter (stationarity + walk-forward + BH-FDR) was
extended with three more independent gates:

  4. **Block-bootstrap 95% CI** (block=60 s, 1000 resamples). Naive
     bootstrap overstates effective N when 1-Hz samples share state;
     moving block of 60s preserves local autocorrelation. Cell passes
     iff the 95% CI on IC excludes the |IC|=0.04 floor (lo > +0.04 or
     hi < −0.04).
  5. **Vol-adjusted IC.** Forward returns scale linearly with
     realized σ. Divide each `fwd_ret_T` by an EWM σ(halflife=600 s)
     and re-measure IC. Pass if same sign and ≥ 50% of the raw
     magnitude — i.e. signal isn't driven by a few high-vol bursts.
  6. **Concurrent-feature correlation.** Pairwise Spearman ρ on
     feature columns themselves; warn on |ρ|>0.7. Catches the case
     where two features are mathematically the same signal counted
     twice.

Re-run on the partial dataset (15.7 h):

| Filter | Survivors |
|---|---:|
| Base hits | 144 / 275 |
| Triple-filter | 89 |
| **+ Bootstrap CI** | **57** ← 32 cells removed |
| **+ Vol-adjusted** | **57** (none removed — signal vol-invariant) |
| **6-filter survivors** | **57** |

Filter 4 was the strongest discriminator — it removed cells whose CI
touched zero, eliminating N-inflated weak hits. Filter 5 preserved
all 57, evidence the signal is robust to vol regime. Filter 6 flagged
duplicates: `depth_imbalance ↔ book_slope_bid/ask` (|ρ| up to 0.83)
and `funding_rate_8h ↔ perp_oi` (ρ=−0.74). After de-duplication the
independent winning features are narrower than the raw 57 suggest.

**Top 6-filter survivors (with bootstrap CI):**

| Pair | Feature | H | IC | CI95 | Vol-adj |
|---|---|---:|---:|---|---:|
| XRP | spread_pct | 1800s | +0.475 | [+0.407, +0.538] | +0.483 |
| ETH | spread_pct | 1800s | +0.400 | [+0.328, +0.475] | +0.326 |
| XRP | basis_pct | 120s | +0.378 | [+0.334, +0.420] | +0.378 |
| BTC | spread_pct | 1800s | +0.361 | [+0.281, +0.436] | +0.316 |
| SOL | funding_rate_8h | 1800s | +0.335 | [+0.262, +0.400] | +0.370 |

**Independent 6-filter winners (after de-duplication) hitting ≥3 pairs:**

- `spread_pct` × {120, 300, 600, 1800}s — 4 pairs (BTC/ETH/SOL/XRP)
- `basis_pct` × {120, 600}s — 3 pairs
- `book_*` cluster (depth_imbalance + book_slope_*) — collapses to
  ONE effective signal that hits 3 pairs
- `funding_rate_8h` (or `perp_oi`, redundant) at slow horizons — 3 pairs

This is strong preliminary evidence for Phase B. The remaining
unknown is 5-day stationarity (still only 2 days of data so far).

## ⚠️ Signal-nature investigation (2026-04-25, post-6-filter)

The 6-filter battery told us *whether* the signals are real. It did
not tell us *how big* the effect is. `microstructure_signal_nature.py`
bins each surviving cell into quintiles by feature value and reports
the conditional mean of the forward return — i.e. the actual basis-
point edge between top and bottom quintiles, which is what matters
for live trading after fees.

| Cell | Q5−Q1 (bps) | Monotonicity ρ | Post-fee net (30 bps RT) |
|---|---:|---:|---:|
| XRP spread_pct@1800s | **+14.23** | +0.899 | −15.77 |
| ETH spread_pct@1800s | +11.77 | +0.883 | −18.23 |
| BTC spread_pct@1800s | +8.45 | +0.961 | −21.55 |
| SOL spread_pct@1800s | +9.37 | +0.996 | −20.63 |
| XRP basis_pct@120s | +4.18 | +0.984 | −25.82 |
| BTC depth_imbalance@60s | +1.21 | +0.981 | −28.79 |
| XRP book_slope_bid@300s | −4.90 | −0.998 | −34.90 |
| AVAX funding_rate_8h@1800s | −17.46 | −0.974 | −47.46 |
| SOL funding_rate_8h@1800s | +14.12 | +0.750 | NOISE (Q3 out of order) |

**Critical finding:**

- IC values are REAL — quintile relationships are cleanly monotonic
  (\|ρ\| ≥ 0.88 on all but one cell)
- BUT magnitudes are ECONOMICALLY TOO SMALL — best case 14.23 bps
  gross edge over a 30-min horizon vs ~30 bps round-trip taker fee
- A taker-execution Phase B strategy on any single feature would
  lose money to fees in expectation

The 6-filter battery missed this because Spearman IC measures rank
correlation, not magnitude. +0.475 IC says "Q5 reliably has higher
returns than Q1" — but only by 14 bps over 30 minutes. Magnitude
must be checked separately.

**ADR-002 reminder:** "L99 minimum edge gate (S5): 0.30% on spot
(was 0.12% on futures)". We have +0.14% gross. Below gate.

**Implications for D6 verdict:**

1. The microstructure thesis is NOT killed. The signals are real;
   the magnitude problem is. The Apr 30 final run on 5 days of data
   may show wider Q5−Q1 spreads (more regime variation captured).
2. Single-feature taker strategy = NOT shippable.
3. Three credible paths forward:
   - **Ensemble compound**: independent winning features
     (spread cluster + basis + book cluster + funding cluster ≈
     4 independent signals after de-duplication). If each adds +5
     bps when they align, an alignment filter that fires on 3-of-4
     could approach +20 bps. Still tight.
   - **Tail filtering**: trade only top-5% / bottom-5% of feature
     values (not 20%-quintiles). Per-trade edge larger, frequency
     much lower. Need to backtest with realistic fill rates.
   - **Maker-only execution**: Gate.io maker fee ≈ 0.10% RT vs
     0.30% taker. Net edge gate becomes +10 bps, achievable on
     XRP spread_pct alone. But maker = passive, fill rate variable,
     slippage risk in fast moves.

4. The SOL funding_rate_8h cell flunks the nature test (Q3 out of
   monotonic order, ρ=0.75). Drop from the survivor list — the high
   IC was driven entirely by Q1+Q5 tail extremities, not a smooth
   relationship. Filter 7 (monotonicity gate) is justified.

## Filter 7 (monotonicity gate) + maker-fee sensitivity — 2026-04-25 update

### Filter 7 added: quintile monotonicity

After the signal-nature investigation found SOL funding_rate@1800s
had IC=+0.32 / monotonicity ρ=+0.75 (Q3 out of order — high IC was
driven by Q1+Q5 tail extremes only), we made monotonicity a hard
gate, not just a verdict. `quintile_monotonicity()` computes
Spearman ρ between quintile rank (1..5) and the per-quintile mean
forward return. Cells with |ρ| < 0.85 are dropped.

7-filter run on the partial dataset:

| Filter | Survivors |
|---|---:|
| Base hits | 138 / 275 |
| 1 · stationarity | 104 |
| 2 · walk-forward | 79 |
| 3 · BH-FDR | 239 / 275 |
| Triple | 79 |
| 4 · bootstrap CI | 53 |
| 5 · vol-adjusted | 53 |
| **6 · monotonicity** | **47 ← removed 6 tail-driven cells** |
| 7 · concurrent-feature | warnings only |

Filter 6 (monotonicity) eliminated 6 cells where the IC was real but
the structure was tail-driven, not smooth. SOL funding@1800s was
correctly caught — confirms the filter's purpose.

### Maker-fee sensitivity run

`microstructure_signal_nature.py --fee-bps-rt 10 20 30 40` returns
post-fee net bps under each fee scenario. Gate.io reference:
maker ≈ 10 bps RT, taker ≈ 30 bps RT.

| Cell | Q5−Q1 (bps) | @10 maker | @20 | @30 taker | @40 |
|---|---:|---:|---:|---:|---:|
| **AVAX funding_rate@1800s** | −17.46 | **✅ +7.5** | 🛑 −2.5 | 🛑 −12.5 | 🛑 −22.5 |
| XRP spread_pct@1800s | +14.23 | ⚠ +4.2 | 🛑 −5.8 | 🛑 −15.8 | 🛑 −25.8 |
| ETH spread_pct@1800s | +11.77 | ⚠ +1.8 | 🛑 −8.2 | 🛑 −18.2 | 🛑 −28.2 |
| BTC spread_pct@1800s | +8.45 | 🛑 −1.6 | 🛑 −11.6 | 🛑 −21.6 | 🛑 −31.6 |
| SOL spread_pct@1800s | +9.37 | 🛑 −0.6 | 🛑 −10.6 | 🛑 −20.6 | 🛑 −30.6 |
| XRP basis_pct@120s | +4.18 | 🛑 −5.8 | 🛑 | 🛑 | 🛑 |
| BTC depth_imbalance@60s | +1.21 | 🛑 −8.8 | 🛑 | 🛑 | 🛑 |

**Strategic implications for Phase B design:**

- **Taker execution:** ZERO single-feature cells profitable. Confirmed.
- **Maker execution (10 bps RT):** ONE single-feature cell profitable
  → AVAX funding_rate_8h@1800s, +7.5 bps net edge. Pattern: high
  positive funding (longs paying shorts) → short the next 30 min.
  Known crypto unwind dynamic.
- **XRP spread_pct@1800s** is borderline (+4.2 bps maker net) —
  realistic slippage on a 30-min horizon would consume that margin.
- **All other signals require ensemble compounding** — alone, none
  cross the maker-fee threshold with usable margin.

This is a much narrower Phase B design space than the 47-cell raw
survivor list suggested, and that's exactly what discipline is
supposed to produce: separating "real but unprofitable signal" from
"real AND tradeable signal."

## D6 plan — Apr 30 (5 days from now)

When the WS collector reaches the 120 h mark:

1. Re-run `microstructure_analyze.py` on the full window.
2. Re-run `microstructure_robust_check.py` with 5 daily buckets for
   stationarity.
3. Add the following BEFORE the verdict counts as binding:
   - **Bootstrap t-stat:** resample 1000× to get a non-parametric CI
     on each surviving cell's IC.
   - **Volatility-adjusted forward returns:** divide each
     `fwd_ret_Ts` by realized σ to compare across regimes.
   - **Spread-vs-mid look-ahead audit:** verify the snapshot
     timestamp truly precedes the forward-return horizon.
   - **Concurrent feature inspection:** if `spread_pct` is just
     the inverse of `book_slope_*`, those features are not
     independent and the apparent breadth is illusory.
4. **Phase B promotion criteria** (from spec): ≥ 1 (feature, horizon)
   combo with |IC| ≥ 0.04, |t| ≥ 2.0, **stable across 4/5 days**, AND
   walk-forward stable. We're tracking 89 candidates that already
   meet 3 of 4 — so Apr 30 should produce a strong verdict.

If 4/5-day stationarity holds → **Phase B greenlit**. Build feature
ensemble classifier, walk-forward via `professional_backtest.py`,
deploy paper-only.

If 4/5-day stationarity fails (signal collapses on more data) →
ADR-002 fallback B1 (on-chain) becomes the next research direction.

---

## What's frozen until Apr 30

- Vote ensemble continues running on all 4 pairs
- ADR-003 still in force (no new strategy code on main)
- No microstructure-based bot deployed
- `microstructure_analyze.py` and `microstructure_robust_check.py`
  are in the toolchain ready for the binding D6 run

---

## Files committed alongside this doc

- `microstructure_robust_check.py` — three-filter robustness sidecar
- `D6_DRYRUN.txt` — verbatim dry-run output (15.7 h data)
- `D6_DRYRUN_ROBUST.txt` — verbatim robust-check output (15.7 h data)
- `D6_DRYRUN_STATUS.md` — this file

The 5-day full run on Apr 30 will append `D6_FINAL.txt` and
`D6_FINAL_ROBUST.txt` so we can diff dry-run vs final and see how the
signal evolved as data accumulated.
