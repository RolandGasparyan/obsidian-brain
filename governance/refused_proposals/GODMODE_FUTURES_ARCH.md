# GODMODE Futures — Architecture (Gate.io USDT Perps, 2–5 min holds)

**Parallel track to the existing spot paper bots.** Spot Vote ≥2 of 3 keeps
running on 4 pairs as OOS evidence collection per the GODMODE_AUDIT
deployment plan. This doc covers the NEW system — microstructure-driven,
maker-biased, latency-aware — built from scratch.

**Scope:** Gate.io USDT-margined perpetual futures. Single contract (BTC_USDT) for
MVP, expanded per validated results. Frankfurt-origin latency budget 150–300ms RTT.

**Philosophy (from the spec):**
> You are not HFT. You are latency-aware structural predator. You trade
> sustained pressure, not noise. No fantasy edge. Only statistically durable
> imbalance.

---

## Module Map

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     GODMODE FUTURES — layered architecture                │
└───────────────────────────────────────────────────────────────────────────┘

 ┌────────────────────────┐   ┌────────────────────────┐
 │ M1. Data Collector     │   │ M2. Replay Engine      │
 │ wss → local L2 book    │──▶│ offline tick replay    │
 │ + trade tape → JSONL   │   │ for agent backtest     │
 │   (godmode/collector)  │   │   (godmode/replay)     │
 └────────────┬───────────┘   └────────────┬───────────┘
              │                            │
              ▼                            ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │                 SIGNAL LAYER — 4 agents, share tick bus              │
 │                                                                       │
 │ ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐    │
 │ │ A1 Microstructure │ │ A2 Volatility     │ │ A3 Liquidity      │    │
 │ │ DIR, STD, persis- │ │ Expansion: ATR,   │ │ Absorption: large │    │
 │ │ tence of pressure │ │ BB squeeze, range │ │ orders w/o follow │    │
 │ └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘    │
 │           └───────────┬─────────┴─────────────────────┘              │
 │                       ▼                                              │
 │         ┌───────────────────────────┐                                │
 │         │ A4 Structural Break       │                                │
 │         │ break + follow-through +  │                                │
 │         │ no wall immediately       │                                │
 │         └──────────────┬────────────┘                                │
 └────────────────────────┼─────────────────────────────────────────────┘
                          ▼
           ┌─────────────────────────────┐
           │    CONFLUENCE ARBITER        │
           │                              │
           │   score =                    │
           │     μstruct × vol_expand     │
           │          × absorption        │
           │          × break_validity    │
           │          × net_edge          │
           │          × risk_state        │
           │                              │
           │ ENTER if score ≥ 78          │
           │   AND net_edge ≥ 0.12%       │
           │   AND risk permits           │
           └──────────────┬───────────────┘
                          ▼
            ┌───────────────────────────┐
            │   A5 Maker Executor        │
            │  post-only limit inside    │
            │   spread, cancel<800ms,    │
            │   repost with fresh book   │
            └──────────────┬─────────────┘
                           │
        ┌──────────────────┴─────────────────┐
        ▼                                    ▼
 ┌─────────────────┐              ┌──────────────────────┐
 │ A6 Fee/Edge     │              │ A7 Risk Throttle     │
 │ Reject if       │              │ 0.6% base, 1.0% agg  │
 │ net < 0.12%     │              │ 2L→0.4%, 3L→30m pause│
 │                 │              │ 3% daily DD → stop   │
 └─────────────────┘              └──────────────────────┘
```

---

## Layer 1 — Data Pipeline

### M1. Data Collector (shipping in this commit)

**Connection:** `wss://fx-ws.gateio.ws/v4/ws/usdt`

**Subscriptions per contract:**
| Channel | Payload | Purpose |
|---|---|---|
| `futures.order_book_update` | `["BTC_USDT", "100ms", "100"]` | Incremental L2 book diffs, 100-level depth, 100ms cadence |
| `futures.trades` | `["BTC_USDT"]` | Public trade tape with aggressive `side` |
| `futures.book_ticker` | `["BTC_USDT"]` | Best bid/ask without delay — redundant safety read |

**Order-book reconciliation (critical — miss this and the book drifts):**

1. Open WS, subscribe to `futures.order_book_update`, buffer all notifications.
2. REST snapshot: `GET /api/v4/futures/usdt/order_book?contract=BTC_USDT&limit=100&with_id=true`
   → returns `id = baseId`.
3. Find first cached notification where `U <= baseId+1 <= u`, apply it and every
   later one. Discard earlier.
4. On each subsequent notification: if `U != local_u+1` → **GAP**. Unsubscribe,
   re-snapshot, re-seed. Do NOT trade on a stale book.
5. Level sizes are ABSOLUTE (not deltas). `size == 0` → delete level.

**Storage:**
- JSONL append files under `godmode/data/`, rotated hourly, format:
  ```
  {"t_ns": 1714034000012345678, "kind": "book_diff",
   "U": 10234, "u": 10237, "bids":[[p,s],...], "asks":[[p,s],...]}
  {"t_ns": ..., "kind": "trade",
   "side": "buy", "price": 67420.1, "size": 3, "id": 98765}
  {"t_ns": ..., "kind": "book_ticker",
   "bid": 67420.0, "ask": 67420.1, "bs": 12, "as": 9}
  ```
- Gitignored; can be shipped to R2/S3 for offline replay later.

**Derived signals computed live (emitted to stdout + a rolling JSON):**
- DIR (Depth Imbalance Ratio) from top-10 levels, every 100ms
- STD (30-second rolling aggressive-buy − aggressive-sell volume)
- Spread (best_ask − best_bid, bps)

**Reliability:**
- Exponential backoff reconnect on WS close (1s, 2s, 4s, max 30s).
- Watchdog: if no message for 15s → force reconnect.
- One process = one contract. Scale by adding processes, not channels per process (keeps reconnect blast radius small).

### M2. Replay Engine (next deliverable after collector accumulates ≥ 24h of data)

Reads JSONL files, yields a unified tick stream in order, feeds the signal
agents as if live. This is how we'll backtest the 7-agent system honestly —
real L2 data, real latency inserted (150–300ms from decision to fill), real
maker-fill simulation (you only fill if your limit price stays at/inside the
inside quote for long enough and the tape prints through you).

---

## Layer 2 — Signal Agents (Modules M3a–M3d)

Each agent is a pure function: `(tick_bus, rolling_state) → score`.
Scores are independently compositable by the Arbiter.

### A1. Microstructure Pressure Engine
- **DIR** = Σ bid_size[1..10] / Σ ask_size[1..10]
  - Bullish if DIR > 1.35 for ≥ 3 consecutive updates
  - Bearish if DIR < 0.75 similarly
- **STD** (30s rolling): aggressive_buy_vol − aggressive_sell_vol, normalized to
  σ of a 10-min rolling baseline. Signal if |Z| > 1.5.
- **Persistence**: both DIR-regime and STD-regime must agree for ≥ 3 updates.
- **Output:** `score ∈ [-100, +100]`, `confidence ∈ [0, 1]`.

### A2. Volatility Expansion Detector
- 1-min ATR, 30-min rolling range percentile, Bollinger-band squeeze (band
  width < 20th percentile).
- Allow entry only if **expanding from contraction** AND not already > 2σ
  extended from mean.
- Output: expansion probability 0–1, directional bias confirmation (sign).

### A3. Liquidity Absorption Monitor
- Track trades aggregated into 1–5 second buckets.
- **Bullish absorption**: large sell flow absorbed at a level, price doesn't
  break down → absorption_buy = true.
- **Bearish absorption**: symmetric.
- **Delta divergence**: price makes new high, aggressive buy delta doesn't →
  warning (exhaustion).
- Output: absorption_strength [0, 100], trap_probability [0, 1].

### A4. Structural Break Engine
- Detect break of 15-min or 30-min high/low.
- Validate with: volume on break > avg, follow-through in next 2 candles,
  no opposite wall appearing in the next 5 seconds.
- Output: break_validity [0, 100], continuation_probability.

---

## Layer 3 — Confluence Arbiter (Module M4)

```
final_score = (A1.score/100) × A2.expansion × (A3.strength/100)
            × (A4.validity/100) × (edge_ok ? 1 : 0) × (risk_permits ? 1 : 0)
            × 100
```

- **Regular entry:** final ≥ 78 AND net_edge ≥ 0.12% AND risk allows.
- **Aggressive entry:** final ≥ 88 AND net_edge ≥ 0.25% AND ≤ 2–3 trades/day.
- **Otherwise NO TRADE.**

Scores are multiplicative so a zero in any single dimension vetoes.

---

## Layer 4 — Execution (Module M5)

**Maker executor:**
- Compute `mid = (best_bid + best_ask) / 2`.
- Post-only limit (`tif: "poc"`) at:
  - **Bullish entry:** best_bid (or best_bid + 1 tick if spread ≥ 3 ticks).
  - **Bearish entry:** symmetric.
- Cancel if not filled within **800ms**, re-evaluate book, repost.
- Max **3 reposts** per entry intent; otherwise abort (signal has decayed).
- **Never taker on entry** (edge budget dies at 0.075% taker fee).
- **Exits:** taker allowed for stop-loss and time-limit exits; maker preferred
  for take-profit.

**Bad-behavior throttle awareness:** Gate.io throttles accounts with poor
fill-ratio to 10–30 req / 10s. With maker-biased cancel-repost we must track
fill_ratio = filled / placed and back off if it falls below 30%.

---

## Layer 5 — Risk (Module M6)

**A6. Fee-aware edge calc:**
```
net_edge = expected_move_pct - (fee_rt + slippage_bp/10000)
```
Assume `fee_rt = 0.06%` (maker entry + taker exit roundtrip, conservative —
verify VIP 0 on actual account first).
Reject if `net_edge < 0.12%`. Aggressive if `net_edge > 0.25%`.

**A7. Risk throttle state machine:**
```
state        base_risk %   triggers
─────────────────────────────────────────────────────
NORMAL       0.6           default
AGGRESSIVE   1.0           enabled only when arbiter score ≥ 88
COOLED       0.4           after 2 consecutive losers
PAUSED       —  (30 min)   after 3 consecutive losers
HALTED       —  (until next day) daily DD ≥ 3%
```
All state changes logged and Telegram-broadcast.

---

## Layer 6 — Exit logic (cross-cutting)

Exit **immediately** on any of:
- Microstructure flips (A1 sign inverts with confidence ≥ 0.6)
- Delta reverses > 2σ
- New liquidity wall appears (≥ 3× rolling-median level size at the touch)
- Time in position > 5 minutes
- Net edge deteriorates (recompute; if < 0.04% → close)

Always respect the stop.

---

## Fee / edge sanity-check

| Component | Value | Source |
|---|---:|---|
| Maker fee VIP 0 (optimistic) | −0.01% rebate | `futures/usdt/contracts/BTC_USDT` contract spec |
| Maker fee VIP 0 (pessimistic) | 0.02% | third-party fee tables |
| Taker fee VIP 0 | 0.05% – 0.075% | contract spec vs third-party disagree |
| **Baseline RT assumption** | **0.06%** | matches spec, covers both scenarios |
| Slippage per side (limit maker) | ~1–3 bps | rare — post-only doesn't cross the spread |
| Slippage per side (taker exit) | 3–10 bps | during vol, can be worse |
| **Conservative RT all-in** | **~0.09%** | assumed in edge calc below |

**Break-even move:** 0.09 % just to cover costs. Any trade under 0.12 %
expected move is filtered by A6.

---

## Deployment safety plan (new system)

Same three-stage discipline as the audit:

**Stage 1a — Data-only (now):** Run M1 collector 24/7 for ≥ 7 days on BTC_USDT
to build the dataset. Zero trading, zero risk.

**Stage 1b — Paper offline replay:** After 7d of data, run M2 replay + A1-A7 +
Arbiter OFFLINE. Measure Sharpe, SQN, fill rate, fee drag, drawdown. Only
if offline SQN > 2 on realistic fills do we paper forward.

**Stage 1c — Paper live:** Connect M5 executor to Gate.io futures in
**paper-shadow mode** (track what orders WOULD have been placed; measure
imputed fill rate given actual book state). ≥ 14 days.

**Stage 2 — Real tiny:** $100 collateral, 1× leverage, full overlay system
active. Telegram two-man rule per entry. ≥ 30 days.

**Stage 3 — Scale:** capped at $1000 until 90 days of Stage 2 with Sharpe > 1.

---

## Open questions to answer with real data

1. **What's the actual VIP 0 fee on your futures account?** (contract spec says
   maker rebate, third-party says 0.02% — login and check Fee page).
2. **What's the typical spread on BTC_USDT futures during normal hours?**
   (This determines how often we can actually fill at best-bid as maker.)
3. **What's the fill-rate baseline on 800ms-canceled post-only orders?** Only
   answerable from recorded data.
4. **What's your Frankfurt → Gate.io RTT distribution?** (p50, p95, p99.) We
   assume 150–300ms; if p99 is 500ms, A5 timing has to widen.

---

## What ships in this commit

1. `godmode/__init__.py`
2. `godmode/collector.py` — Module 1, WebSocket L2 + tape collector, derived
   DIR/STD signals, JSONL writer
3. `requirements-futures.txt` — `websockets`, `aiohttp`
4. `.gitignore` update to exclude `godmode/data/*.jsonl`

Everything else (M2-M7, agents, arbiter, executor) ships in follow-up
commits after Module 1 is producing real data we can reason about.

Do NOT enable real-money futures trading until all seven layers are built,
validated in offline replay, and cleared in ≥ 30 days of paper-shadow mode.
