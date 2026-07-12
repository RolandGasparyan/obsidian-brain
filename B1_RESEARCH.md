# B1 On-Chain Research — Phase B fallback design

**Triggered by:** D6 BINDING 🛑 NO-GO ([wiki/findings/2026-04-30-d6-binding-no-go.md](wiki/findings/2026-04-30-d6-binding-no-go.md)) — 24 cells survive 7-filter battery, 0 maker-fee winners.
**Path:** [PHASE_B_DECISION_TREE.md](PHASE_B_DECISION_TREE.md) branch B.2.3
**Status:** Research artifact on `feat/b1-onchain-research`. NOT merged to main pre-D7. ADR-003 honored.
**D7 expiry:** 2026-05-01 ~00:00 UTC (~10 hours from now)

---

## Problem

5 convergent rigor levels confirm: **single-class microstructure on Gate.io spot at 30 bps fees has no tradeable edge.** The data is L1 order book + tape + perp basis — no edge survives the fee gate.

Per ADR-002 fallback rule, the next research direction is **B1 on-chain** — an entirely different signal class with established academic + practitioner evidence.

## Why on-chain might work where microstructure failed

| Microstructure (failed) | On-chain (B1 candidate) |
|---|---|
| Sub-minute / 30-min horizons | Hours / days / weeks |
| L1 order book (fee-bound) | UTXO / address state (fee-independent for signal extraction) |
| 14 bps gross < 30 bps RT fee | NVT/MVRV/SOPR signals can predict 40-120% moves over 90 days |
| Symmetric noise | Asymmetric signal (large-holder behaviour) |
| One regime captured | Spans full cycle phases |

On-chain signals operate on **slower horizons where Q5−Q1 magnitudes can dwarf fees** because the underlying move is days-to-weeks, not minutes.

## Top candidate signal classes

### Tier 1 — established academic + practitioner edge

| Signal | What it measures | Where it leads | Source |
|---|---|---|---|
| **MVRV ratio** | Market value / realised value — overvalued vs undervalued | <1.0 = capitulation buy zone (305 days bear 2018-19 → triple-digit returns; 178 days 2022 → triple-digit returns) | Glassnode, CryptoQuant |
| **SOPR (aSOPR)** | Spent output profit ratio — are coins moving at profit or loss | aSOPR reclaiming 1.0 after suppression preceded 40-120% rallies in 90 days every cycle since 2018 | Glassnode |
| **NVT ratio** | Network value / on-chain volume — network "P/E ratio" | High NVT = overvalued; low = undervalued | CryptoQuant |
| **Exchange netflow** | Net BTC/ETH moving on or off centralised exchanges | Outflow = accumulation/HODL; inflow = sell pressure | CryptoQuant |
| **Miner outflow / MPI** | Miner-to-exchange transfers vs 1y MA | High = miner selling pressure | CryptoQuant |

### Tier 2 — emerging / faster cadence

| Signal | What | Why interesting |
|---|---|---|
| **Whale Alert transactions** | $1M+ on-chain transfers, real-time | Sub-day latency; identifies large-holder activity |
| **Stablecoin reserves** (USDT/USDC) | Stablecoins held on exchanges | Rising reserves = dry powder for buying |
| **Funding rate divergence** | Perp funding vs spot velocity | Already in our microstructure suite but might combine differently with on-chain |
| **Whale addresses count** | # addresses holding > threshold | Wealth concentration shifts |

### Tier 3 — high-noise, lower priority

- Active addresses (high noise, network growth proxy)
- Hash rate (laggy, infrastructure not signal)
- Mempool size (short-horizon, microstructure-adjacent)

## Data source comparison (priced for our budget)

| Source | Free tier | Paid tier | Coverage | Recommendation |
|---|---|---|---|:---:|
| **CryptoQuant** | many metrics free | Advanced $29/mo, Pro $99/mo, Premium $799/mo | exchange flows + miner behavior + supply | ⭐ start free tier |
| **Glassnode** | basic charts free; API gated | Advanced $29/mo (annual) | MVRV, SOPR, NVT, deepest BTC/ETH on-chain | ⭐ start free tier |
| **Santiment** | free + Pro $44/mo + Pro+ $225/mo | comprehensive + social sentiment | broad asset coverage + crowd psychology | ⚠ social signals risky |
| **Whale Alert** | 10 req/min, 30-day history | Personal $39/mo (60 req/min) | real-time large-tx alerts | ⭐ free tier OK for collection |
| **Coin Metrics** | community tier | enterprise tier | clean academic metrics | ⚠ enterprise pricing |
| **DeFiLlama** | free | — | TVL across DeFi | ⚠ macro proxy only |
| **Etherscan / blockstream.info** | free | — | raw chain data | 🛑 too low-level |

**Recommended starting stack:**
1. CryptoQuant free tier — exchange flows, miner outflows
2. Glassnode free charts API — MVRV, SOPR, NVT
3. Whale Alert free API — sub-day large-transaction stream
4. Defer paid tiers until 5-day collection cycle proves signal viability

## Architecture proposal — `onchain_collector.py`

Mirror the proven `microstructure_collector.py` pattern:

```
┌─────────────────────────────────────────────────────────────┐
│  onchain_collector.py  (NEW, post-D7)                        │
│                                                              │
│  poll_loop (every 5 min — slow cadence is fine):             │
│    ├─ CryptoQuant /exchange/netflow   → BTC/ETH netflow      │
│    ├─ CryptoQuant /miner/outflow      → miner sell pressure  │
│    ├─ Glassnode /metrics/mvrv         → MVRV per asset       │
│    ├─ Glassnode /metrics/sopr         → SOPR per asset       │
│    ├─ Glassnode /metrics/nvt          → NVT per asset        │
│    └─ Whale Alert /transactions       → large-tx stream      │
│                                                              │
│  Compute features for each timestamp:                        │
│    ─ exchange_netflow_btc_z          (z-score over 30d)      │
│    ─ miner_outflow_z                                         │
│    ─ mvrv_btc / mvrv_eth                                     │
│    ─ sopr_btc / sopr_eth                                     │
│    ─ nvt_btc                                                 │
│    ─ whale_tx_count_1h_btc / whale_tx_volume_1h_btc          │
│                                                              │
│  Write parquet hourly:                                       │
│    /var/log/onchain/YYYY-MM-DD/HH/{feature}.parquet          │
│                                                              │
│  Run microstructure_robust_check.py on this schema once      │
│  5+ days of data accumulated.                                │
└─────────────────────────────────────────────────────────────┘
```

**Key design choices:**
- 5-min polling (vs 1Hz microstructure) — these signals move on minutes/hours, not ms
- Same parquet schema pattern → same `microstructure_robust_check.py` 7-filter battery + `microstructure_signal_nature.py` quintile work, ZERO new validation code needed
- Z-scoring of flow metrics within asset (so cross-asset comparable)
- Forward-return horizons: 1h / 4h / 1d / 7d (much wider than microstructure 60s-1800s)

## Forward-return horizons

| Horizon | Why it matters | Fee gate impact |
|---|---|---|
| 1h | Fast on-chain reactions (whale alerts, sudden netflow) | 30 bps fee gate same |
| 4h | Half-day positioning shifts | gate same |
| 1d | Daily MVRV/SOPR moves | gate same |
| 7d | Multi-day capitulation/recovery cycles | **Q5−Q1 of MVRV historically > 100% over 12 months → fee gate trivial** |

The 7-day horizon is the killer feature: signal magnitudes are 100-1000× larger than microstructure, so the 30 bps fee gate becomes negligible. **This is exactly why on-chain is the right pivot.**

## Deployment plan (post-D7)

| Phase | Action | Time |
|---|---|---|
| D7 day 1 | Sign up free tiers (CryptoQuant + Glassnode + Whale Alert) | 30 min |
| D7 day 1 | Build `onchain_collector.py` (mirror microstructure pattern) | 4-6h |
| D7 day 2-7 | Collect 5+ days of data | 5+ days passive |
| D7 day 8 | Run 7-filter battery on collected features | 30 min |
| D7 day 8 | Run signal-nature quintile + multi-horizon | 30 min |
| D7 day 9 | If any cell survives → 4-gate validate (`rsi2_validate.py`-equivalent) | 1 day |
| D7 day 10+ | If validated → Stage 1 paper deploy | gated |

## What we explicitly DON'T do post-D7

- ❌ Build a "max profit predictor" engine on null-edge microstructure data
- ❌ Install MiroShark for narrative simulation as primary signal
- ❌ Run futures (separate ADR + 4-gate per ADR-002)
- ❌ Skip the 5-day collection / 7-filter / signal-nature pipeline — same discipline applies

## ADR-003 compliance pre-D7

This document is **research only**. No code is written. Lives on `feat/b1-onchain-research`. Will NOT merge to `main` until D7 (May 1).

After D7:
- `onchain_collector.py` is NEW strategy code → goes through PR review + tests
- Initial 5-day collection runs on VPS as a new systemd service (`onchain-collector.service`)
- Existing 7-filter validation toolchain runs unchanged on the new data

## Sources

- [CryptoQuant — Exchange Flows](https://userguide.cryptoquant.com/cryptoquant-metrics/exchange/exchange-in-outflow-and-netflow)
- [Glassnode pricing](https://glassnode.com/) — Advanced $29/mo, Pro $99/mo
- [BingX — Top 10 On-Chain Tools 2026](https://bingx.com/en/learn/article/what-are-the-top-on-chain-analysis-tools-for-crypto-traders)
- [Whale Alert API docs](https://docs.whale-alert.io/) — 10 req/min free
- [ScienceDirect — On-chain features outperform price+volume](https://www.altcointrading.net/bitcoin-price-forecasting-with-ml-models/) (2025 paper cited)
- [Spoted Crypto — MVRV/SOPR bottom signals](https://www.spotedcrypto.com/bitcoin-onchain-bottom-signals/)
- [PHASE_B_DECISION_TREE.md](PHASE_B_DECISION_TREE.md) branch B.2.3
- [wiki/findings/2026-04-30-d6-binding-no-go.md](wiki/findings/2026-04-30-d6-binding-no-go.md)

---

_Generated 2026-04-30, pre-D7. Research-only artifact on `feat/b1-onchain-research`. Will be the basis for D7+1 implementation work after ADR-003 expires._
