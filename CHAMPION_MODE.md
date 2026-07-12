# Champion Mode — L99 Apex Doctrine

**$3,000 → $1,000,000.** The full mathematical blueprint and execution
discipline. This is the project's north star. Every other doc and every line
of code in this repository is judged by whether it honors what's written here.

> *Most traders will not reach \$1M from \$3k. Not because the math is wrong.
> Because the psychology is harder than the math.*

---

## I. The honest brief

333× return is not impossible. It is also not likely on any short timeline.

| Time horizon | Required CAGR | Monthly | Realistic? |
|---|---:|---:|---|
| 1 yr | 33,233% | +215% | No |
| 3 yr | 621% | +16.5% | Very hard |
| 5 yr | 197% | +8.8% | Aggressive |
| **7 yr** | **100%** | **+6.0%** | **Achievable** |
| 10 yr | 56% | +3.8% | Realistic |

**Champion target: 5–7 years, ~200% CAGR, 8–10% monthly net.**
Top 0.1% of algo traders sustained for 5–7 years. That is the bar.

---

## II. The Four Capital Stages (mandatory regression)

| Stage | Capital | Mode | Monthly | Risk/trade | Trades/mo |
|:---:|---|---|---:|---:|---:|
| **1** | $3k → $20k | Ultra Aggressive | 12–15% | 1.5% | 15–20 |
| **2** | $20k → $150k | Controlled Aggression | 8–12% | 1.0% | 10–15 |
| **3** | $150k → $500k | Optimized Risk | 5–8% | 0.75% | 6–10 |
| **4** | $500k → $1M | Capital Preservation | 3–5% | 0.5% | 4–6 |

**Stage regression rule (immutable):** if equity drops back to a previous
stage boundary, revert to that stage's risk rules immediately. No pride.
No ego. The compound is sacred.

---

## III. Three engines, one mission

| Engine | Type | Pair universe | Hold | Risk | Stage 1 alloc | Stage 4 alloc |
|---|---|---|---|---:|:---:|:---:|
| **aegis-microstructure** | Order-flow | Gate.io futures BTC/ETH | 2–5 min | 0.6–1.0% | 40% | 10% |
| **aegis-alpha** | Momentum | Gate.io spot top 50 alts | 4–72 h | 1.0–2.0% | 40% | 30% |
| **quant-predator** | MTF trend | BTC + top 20 alts trending | 2–14 d | 1.5–2.0% | 20% | 60% |

**State machine — TWO states only:**
- **STATE A (default):** 100% USDT. Engine scanning. No coin exposure.
- **STATE B:** capital deployed in ONE token. TP / stop / time-limit set.
  Exit ALWAYS returns to STATE A.

**Hard rules:**
- No two positions simultaneously (Stage 1–2). Max 2 (Stage 3+).
- No B → B (no rolling between trades without USDT touch).
- No revenge trades. No moving stops further. No averaging down.

---

## IV. Trade mathematics (the EV table)

Minimum viable EV per trade: **+0.75R**.

| Win rate | Min avg-win for +EV |
|---:|---:|
| 40% | 1.6R (very hard) |
| 45% | 1.3R |
| **50%** | **1.1R (standard threshold)** |
| 55% | 0.9R |
| 60% | 0.75R (excellent) |

**Champion target: 52–58% WR · 2.0–3.0R avg win · EV ≥ +0.75R.**

At 1.5% risk on $3,000: EV per trade = $33.75 → ~+22%/month at 20 trades.

**Required trade count to $1M:** ~2,800–3,200 over the journey.

---

## V. Risk laws (5 layers, each immutable)

### Layer 1 — Trade
- ≤ 2% risk Stage 1, ≤ 1% Stage 3+
- Stop placed BEFORE entry. Never moved further.
- No averaging down. No revenge.

### Layer 2 — Daily
- 5% daily DD → close all, no more trades today
- 3 consec loss days → −25% size 5 days

### Layer 3 — Weekly
- Net negative week → −25% size next week
- −10% week → 48h pause + strategy review
- −15% from peak → minimum size + ML signal review

### Layer 4 — Stage regression
- Equity drops to previous stage boundary → revert to lower-stage rules

### Layer 5 — Systemic
- BTC drops > 20% in 7 days → 100% USDT, ALL engines off
- > 80% on any single exchange forbidden above $50k
- Above $200k → hardware-wallet buffer for non-trading capital

---

## VI. Statistical viability gates (6-month live sample)

System is VIABLE only if ALL of these hold:

| Metric | Min | Champion |
|---|---:|---:|
| Win rate | 48% | 55–60% |
| Avg R per win | 2.0 | 2.5–3.5 |
| EV per trade | +0.48R | +0.85R |
| Profit factor | > 1.3 | > 1.8 |
| Max consec losses | ≤ 8 | ≤ 6 |
| Max drawdown | < 20% | < 12% |
| Monthly Sharpe | > 0.8 | > 1.5 |
| Monthly net return | > 5% | 8–12% |

**If any falls below MIN at 50+ live trades — STOP. Redesign. Do not
add capital to a broken system.**

---

## VII. Probability of success

| Scenario | Discipline | P($1M @ 7y) | P($500k @ 7y) | P(ruin @ 3y) |
|---|---|---:|---:|---:|
| **Champion** (55% WR, 2.5R, strict) | Perfect | ~18% | ~35% | ~4% |
| Average (50% WR, 2.0R, some slip) | Good | ~7% | ~15% | ~9% |
| Undisciplined (48%, 2.0R, emotional) | Poor | ~2% | ~5% | ~28% |

**Same signal, different execution = Champion vs Undisciplined.**
The signal is not the strategy. The discipline is.

---

## VIII. The eight failure points (the silent killers)

1. **Oversizing at Stage 1** — 5%/trade → 8-loss streak = −34% → break
2. **Moving stops** — 1R loss → 3R loss → win-rate must compensate 3×
3. **Overtrading** — 40 trades × 0.1% fee = 4% drag before any loss
4. **BTC correlation ignorance** — alts move 2× BTC in crashes
5. **Stage creep** — using Stage 2 sizes at Stage 1 equity
6. **Overfit signal** — backtest 70% WR → live 45% WR
7. **Emotional regime change** — skip 3 signals → all 3 win → frustration
8. **Exchange risk** — full capital at one venue → exchange incident = total loss

---

## IX. Realistic timeline (champion scenario)

| Month | Equity | Stage |
|---:|---:|:---:|
| 0 | $3,000 | 1 |
| 12 | $12,800 | 1 |
| 24 | $38,000 | 2 |
| 36 | $105,000 | 2→3 |
| 48 | $230,000 | 3 |
| 60 | $440,000 | 3→4 |
| 72 | $760,000 | 4 |
| **82** | **$1,000,000+** | **TARGET** |

**Realistic 6.5–7 yr · Median 8–10 yr · Optimistic 4–5 yr · Pessimistic
12–15 yr (still surviving).**

---

## X. The Champion Code

> **I.** USDT is the weapon. Coins are the battlefield. Visit, extract, return.
>
> **II.** Math before emotion. Size correctly or lose eventually.
>
> **III.** Three engines, one mission. Microstructure — momentum — multi-timeframe.
>
> **IV.** Risk before edge. Edge before ego. Discipline before everything.
>
> **V.** USDT is always one trade away. Never hold what you would not buy now.

---

## What's currently built vs what's missing

### ✅ Built (live or proven)
| Component | Where | State |
|---|---|---|
| Spot Vote ≥2 of 3 paper bots | `gods_level_engine.py` `VoteEnsembleStrategy` | running 4 pairs on VPS, audit-confirmed marginal-at-best edge |
| Walk-forward + Monte Carlo + portfolio + 70/30 | `walk_forward.py`, `param_sweep.py`, `regime_gated_ma.py`, `mean_reversion.py`, `deep_edge.py`, `max_edge.py`, `professional_backtest.py` | research arsenal complete |
| Telegram alerts + kill switch + HTTPS | `telegram_alerts.py`, `bot_control.py`, nginx | live infrastructure |
| `aegis-microstructure` foundation | `godmode/` — collector, replay, 7 streams, arbiter, runtime | M1+M2+M3 wired; Streams 3/4/6 stubbed |

### ⏳ Missing (priority order)
| # | Component | Spec § |
|---:|---|---|
| 1 | **aegis-alpha** scanner — 4H scoring on Gate.io spot top 50 | §3.1 — building NOW |
| 2 | aegis-alpha — entry/exit + TP ladder + trailing logic | §3.2-3.3 |
| 3 | Capital stage tracker + dynamic position sizer (used by all 3 engines) | §4.1 |
| 4 | Win-streak + loss-throttle + volatility scaler | §4.1 |
| 5 | Risk overlay layers 2-4 (daily DD 5% kill, weekly DD review, stage regression) | §5 |
| 6 | godmode microstructure — replace S3/S4 stubs with real logic | §3 |
| 7 | godmode — wire MakerFillSim + post-only executor → live paper-shadow | §6 |
| 8 | quant-predator — MTF momentum scanner + entry trigger | engine 3 |
| 9 | ML module (LightGBM regime classifier) | §8.3 |
| 10 | Statistical-viability gate enforcer (auto-pause if drift) | §6 |

### 🛑 Pre-conditions for ANY real capital
Per the GODMODE audit and the doctrine's Section VI:
- 50+ live trades in paper-shadow mode
- All 8 viability metrics above MIN
- Live win rate within 10pts of backtest win rate
- 30+ days of clean infrastructure (no missed entries, no failed exits)

The CHAMPION_MODE.md doctrine is the source of truth.
The code in this repository serves it, not the other way around.
