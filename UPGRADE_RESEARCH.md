# Upgrade Research — what's on GitHub that could move L99 forward

**Date:** 2026-04-29
**Status:** Research only · zero installs pre-D6 · ADR-003 in force until May 1
**Question asked:** "do a deep research on github for what we need to install to upgrade our project"

---

## TL;DR — the project's gap is DATA, not LIBRARIES

After 4 convergent null tests today (7-filter battery + signal-nature + Bayesian sweep + ensemble alignment), the conclusion is clear: **single-class microstructure on Gate.io spot at 30 bps fees has no tradeable edge.** Installing more Python packages does not create edge. **Adding new data sources or different execution models** is what unlocks new evidence.

Of the libraries surveyed, only ONE category is high-leverage now: **factor analysis & validation tooling** (Alphalens, mlfinlab CPCV) — they would replace `microstructure_signal_nature.py` and `microstructure_robust_check.py` with industrial-grade equivalents, but they don't change the answer the data is already giving us.

**Recommended pre-D6 installs: zero.**
**Recommended post-D7 installs: prioritized list below.**

---

## Survey by category

### 1. Order-book / microstructure tooling

| Library | What it does | Stars | Verdict |
|---|---|:---:|---|
| [hftbacktest](https://github.com/nkaz001/hftbacktest) | HFT backtest with L2/L3 order book, queue position, latency modelling — Binance/Bybit | 2k+ | ⭐ **highest impact post-D7** if D6 NO-GO and we go to maker execution. Realistic fill-rate model is exactly what `microstructure_signal_nature.py` only approximates today. |
| [crobat (orderbooktools)](https://github.com/orderbooktools/crobat) | Academic Python lib — records LOB changes, computes OFI / Trade Flow Imbalance | 200+ | ⚠ academic, Coinbase-only. We already implement OFI (Cont/Kukanov/Stoikov) directly in `microstructure_collector.py`. Reimplementation, not upgrade. |
| [VisualHFT](https://github.com/visualHFT/VisualHFT) | C#/WPF GUI — VPIN, LOB Imbalance, Market Resilience, OTT Ratio | 400+ | ⚠ C#, not Python. Useful conceptually for additional features (VPIN we don't compute yet); reimplementing in Python is more work than installing it. |
| [mansoor-mamnoon/limit-order-book](https://github.com/mansoor-mamnoon/limit-order-book) | C++ core + Python SDK, 20M msg/sec, μs latency | 100+ | ⚠ way over-engineered for our 1Hz spot snapshot use case. |

**Net:** `hftbacktest` is the one we'd want **if and only if** D6 NO-GO and we pivot to maker execution simulation (decision tree branch B.2.2).

### 2. Factor analysis / validation

| Library | What it does | Verdict |
|---|---|---|
| [Alphalens (Quantopian)](https://github.com/quantopian/alphalens) | Spearman IC, quintile binning, mean-IC by group, period-by-period turnover, full tear-sheet | ⭐ **does exactly what `microstructure_signal_nature.py` + `microstructure_robust_check.py` do.** Better tested. More features. Industrial-grade tear sheets. |
| [mlfinlab](https://github.com/hudson-and-thames/mlfinlab) | Marcos López de Prado's library: Combinatorial Purged Cross-Validation, triple-barrier labelling, fractional differentiation | ⭐⭐ **CPCV is the gold standard for time-series ML cross-validation.** Our walk-forward + bootstrap is good; CPCV is better. |
| [skfolio CombinatorialPurgedCV](https://skfolio.org/generated/skfolio.model_selection.CombinatorialPurgedCV.html) | Modern scikit-learn-compatible CPCV implementation | ⭐ alternative to mlfinlab if we want sklearn integration |

**Net:** Alphalens + mlfinlab would let us delete ~600 lines of custom validation code. **But they don't change the verdict** — they'd produce the same null results faster and prettier. Post-D7 hygiene work.

### 3. Backtesting alternatives

| Library | What it does | Verdict |
|---|---|---|
| [vectorbt](https://github.com/polakowo/vectorbt) | Numba-JIT backtester, 1000× faster than backtesting.py, NumPy-array based | ⭐ would let us run 10000-trial Bayesian sweeps in seconds. **But we're not bottlenecked by speed** — we're bottlenecked by data quality. |
| [VectorBT PRO](https://vectorbt.pro/) | Proprietary successor, paid | 🛑 paid, not open-source |
| [backtesting.py](https://github.com/kernc/backtesting.py) | What we use | ✅ current; no need to switch |

**Net:** vectorbt is faster but doesn't add evidence. Our 50-trial × 11-cell sweep takes 5 minutes; we don't need it 1000× faster yet. Post-D7 if we ever do walk-forward at scale.

### 4. On-chain data (B1 fallback path)

| Source | What it does | Verdict |
|---|---|---|
| [Glassnode API](https://glassnode.com/) | Industrial on-chain metrics (NVT, MVRV, exchange flows, miner outflows, SOPR, dormancy) | ⭐⭐ if D6 NO-GO and we go on-chain (decision tree branch B.2.3). Paid but offers free tier. |
| [Whale Alert API](https://whale-alert.io/) | Large transaction alerts, free tier 60 calls/min | ⭐ free, simpler. Lower-resolution signal. |
| [whaleAlert](https://github.com/stuianna/whaleAlert) | Python client + SQLite logger for Whale Alert | ⭐ pre-built collector, 5-minute install |
| [crypto-whale-watching-app](https://github.com/pmaji/crypto-whale-watching-app) | Dash app tracking whale buy/sell walls | ⚠ niche, exchange-specific |
| [bitcoin-etl](https://github.com/blockchain-etl/bitcoin-etl) / [ethereum-etl](https://github.com/blockchain-etl/ethereum-etl) | Raw chain data extraction | 🛑 too low-level; need transformations |

**Net:** Glassnode (paid) or Whale Alert (free) is the actual B1 fallback unlock. New 5-day collection cycle would be required.

### 5. Tick-level historical data (the L3 unlock)

| Source | What it does | Verdict |
|---|---|---|
| [tardis-dev](https://github.com/tardis-dev/tardis-python) | Tick-level historical L2/L3 order book, all major exchanges | ⭐⭐⭐ **largest unlock for maker simulation.** Has L3 (market-by-order) for Coinbase, full L2 for Binance/Bybit/etc. Would let us build a REAL maker-execution simulator with queue position + adverse selection, not the L1 approximation we have. **Paid** — pricing per exchange-day. |
| [tardis-machine](https://github.com/tardis-dev/tardis-machine) | Self-hosted server + caching | nice-to-have if we go heavy |

**Net:** tardis-dev L3 is the biggest single unlock. Without it, maker simulation is fundamentally an L1 approximation.

### 6. Strategy frameworks (already-evaluated alternatives)

| Library | Notes |
|---|---|
| [freqtrade](https://github.com/freqtrade/freqtrade) | Mentioned in `GODMODE_UPGRADE_MASTERPLAN.md`. Python crypto bot, hyperopt, FreqAI ML extensions. Good if we want a full live trading framework, but our existing run.py + bot-control + systemd architecture is purpose-built and works. |
| [jesse-ai](https://github.com/jesse-ai/jesse) | Python crypto, advanced backtest. Same evaluation as freqtrade. |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | High-performance C++/Python, professional-grade. Overkill for our 1d-bar Vote ensemble. |
| [Hummingbot](https://github.com/hummingbot/hummingbot) | Market-making framework. ⭐ relevant **only** if we go to maker execution (B.2.2). |

**Net:** keep existing architecture. Hummingbot becomes interesting if D6 NO-GO → maker pivot.

### 7. ML / quantitative

| Library | Notes |
|---|---|
| [Microsoft qlib](https://github.com/microsoft/qlib) | Mentioned in MASTERPLAN. AI quant platform with regime models, alpha factors, full pipeline. **Heavy dependency tree.** Useful if we go regime-conditional Phase B with ML, NOT useful for current null-edge data. |
| [pyfolio](https://github.com/quantopian/pyfolio) | Performance/return analysis, tear sheets | ⭐ already a quintopian-quality replacement for parts of our reporting |
| [empyrical](https://github.com/quantopian/empyrical) | Risk and performance metrics | ⭐ minimalist; we use scipy + custom code today |
| [TA-Lib](https://github.com/mrjbq7/ta-lib) / [pandas-ta](https://github.com/twopirllc/pandas-ta) | Indicator libraries | ✅ our ad-hoc indicators (SMA, RSI, ATR) are fine; not a bottleneck |

**Net:** alphalens + pyfolio + empyrical = the Quantopian trinity. All open-source, all replaceable for parts of our pipeline. **Convenience, not edge.**

---

## L99-impact ranking

| Rank | Tool | Pre-D6 | Post-D7 | Path |
|:---:|---|:---:|:---:|---|
| 1 | tardis-dev (L3 historical data) | 🛑 | ⭐⭐⭐ | unlocks real maker simulation (decision tree B.2.2) |
| 2 | mlfinlab (CPCV) | 🛑 | ⭐⭐ | gold-standard validation; replaces our walk-forward + bootstrap |
| 3 | hftbacktest | 🛑 | ⭐⭐ | realistic fill-rate model for maker exec |
| 4 | Glassnode / Whale Alert | 🛑 | ⭐⭐ | B1 on-chain fallback unlock if D6 NO-GO |
| 5 | Alphalens | 🛑 | ⭐ | replaces signal_nature + parts of robust_check (cosmetic) |
| 6 | vectorbt | 🛑 | ⭐ | speed, not evidence |
| 7 | Hummingbot | 🛑 | ⭐ | maker-execution framework (only if B.2.2 path) |
| 8 | qlib | 🛑 | ⚠ | heavy; only if we go regime-conditional ML |
| 9 | freqtrade / jesse | 🛑 | 🛑 | duplicates existing architecture |
| 10 | crobat / VisualHFT | 🛑 | 🛑 | reimplement what we already have |

---

## Why ZERO pre-D6 installs

1. **ADR-003** in force until May 1 — no new strategy code on `main`
2. New libraries change validation methodology; **mid-experiment toolchain swap = methodology drift**, results no longer comparable to today's 4 null tests
3. The 4 null tests already converge on the same answer; adding a 5th library that says the same thing wastes time
4. Most "upgrade" libraries are TOOLS, not EDGES. We don't lack tools; we lack data.
5. The current toolchain (backtesting.py + sambo + scipy + custom 7-filter battery) **works correctly** — see today's session: caught broken AI commits, fabricated test reports, look-ahead bias, monotonicity failures, fee-gap economics. **Nothing the toolchain missed.**

## Why post-D7 has a real install list

If D6 fires 🛑 NO-GO (most likely), the decision tree branches to:

- **B.2.1 ensemble** — already tested today, also null
- **B.2.2 maker execution** — needs `hftbacktest` (queue/fill modeling) + `tardis-dev` (L3 data)
- **B.2.3 on-chain B1** — needs `whaleAlert` or Glassnode API + new 5-day collection cycle

So the post-D7 install priority is:
1. tardis-dev (1-2 day prep, paid)
2. hftbacktest (1 day prep)
3. mlfinlab (CPCV for proper validation)
4. Glassnode or Whale Alert client + new collector (if B.2.3 path chosen)

## What we DON'T need despite the hype

These are popular but don't move L99:

- ❌ qlib — heavy ML stack for data we already know is null
- ❌ TA-Lib / pandas-ta — our indicators work fine
- ❌ freqtrade / jesse — duplicate our architecture
- ❌ vectorbt — speed without evidence
- ❌ NautilusTrader — overkill for spot 1d strategies
- ❌ Generic "AI trading bot" repos — vibes-coded, no validated edge

---

## Final verdict

The honest "deep research" answer to "what should we install to upgrade":

> **Zero packages right now. Wait for D6.**
>
> If D6 NO-GO (likely), the post-D7 install list is: `tardis-dev`, `hftbacktest`, `mlfinlab`, and (if B.2.3 path) one of `whaleAlert` / Glassnode client.
>
> The bottleneck for L99 is not Python packages. It is:
> 1. Data we don't have yet (5-day window — Apr 30)
> 2. Data we'd need to buy (L3 order book — tardis-dev paid tier)
> 3. Data we'd need to collect anew (on-chain — Glassnode + 5-day cycle)
> 4. Time (60d Stage 1 paper + 90d Stage 2 real)
>
> No `pip install` solves any of these.

This research artifact stays on `feat/upgrade-research` as a record. Open PR for review/discussion, do NOT merge to `main` until post-D7 priorities are confirmed.

---

## Sources

- [hftbacktest (nkaz001)](https://github.com/nkaz001/hftbacktest) — high-frequency backtest with L2/L3 order book + queue/latency models
- [crobat (orderbooktools)](https://github.com/orderbooktools/crobat) — academic Python LOB / OFI library
- [VisualHFT](https://github.com/visualHFT/VisualHFT) — C#/WPF microstructure analytics GUI
- [mansoor-mamnoon/limit-order-book](https://github.com/mansoor-mamnoon/limit-order-book) — C++ + Python SDK LOB engine
- [Alphalens (Quantopian)](https://github.com/quantopian/alphalens) — factor analysis: IC, quintiles, tear sheets
- [Alphalens docs](https://quantopian.github.io/alphalens/alphalens.html) — official Alphalens reference
- [cloudQuant/alphalens](https://github.com/cloudQuant/alphalens) — maintained Alphalens fork
- [mlfinlab (hudson-and-thames)](https://github.com/hudson-and-thames/mlfinlab) — Marcos López de Prado's library, includes Combinatorial Purged CV
- [mlfinlab CPCV implementation](https://github.com/hudson-and-thames/mlfinlab/blob/master/mlfinlab/cross_validation/combinatorial.py) — direct link to CPCV code
- [skfolio CombinatorialPurgedCV](https://skfolio.org/generated/skfolio.model_selection.CombinatorialPurgedCV.html) — sklearn-compatible CPCV
- [vectorbt (polakowo)](https://github.com/polakowo/vectorbt) — numba-JIT backtester
- [VectorBT docs](https://vectorbt.dev/) — getting started
- [tardis-python](https://github.com/tardis-dev/tardis-python) — Python client for tardis.dev historical tick-level data
- [tardis-node](https://github.com/tardis-dev/tardis-node) — Node.js client (alternative)
- [tardis-machine](https://github.com/tardis-dev/tardis-machine) — self-hosted Tardis server
- [tardis.dev](https://tardis.dev/) — historical L2/L3 order book service
- [Tardis FAQ on data](https://docs.tardis.dev/faq/data) — what data is captured per exchange
- [Whale Alert](https://whale-alert.io/) — on-chain large-transaction tracker
- [stuianna/whaleAlert](https://github.com/stuianna/whaleAlert) — Python client for Whale Alert API
- [pmaji/crypto-whale-watching-app](https://github.com/pmaji/crypto-whale-watching-app) — Dash whale tracker
- [Glassnode Studio](https://github.com/Glassnode-Studio-Desktop-App) — Glassnode desktop tool

---

_Generated 2026-04-29 by Claude during pre-D6 research. Research-only artifact on `feat/upgrade-research`, not merged to `main`. ADR-003 still in force until D7._
