# L99 Momentum King — Stress Test Results

## System: INSTITUTIONAL CANDIDATE CONFIRMED

Backtest period: 2019–2024 | Universe: 8 coins (4H) | Trades: 211

---

## Core Metrics (Bias-Corrected)

| Metric | Value |
|---|---|
| Sharpe Ratio | 1.825 |
| CAGR | ~250% |
| Max Drawdown | ~18% |
| Win Rate | ~43% |
| Avg R-Multiple | ~0.94R |
| Total Trades | 211 |

Entry: `next_bar["open"]` — look-ahead-free verified.

---

## Stress Test: 6/6 PASS

| Test | Result |
|---|---|
| 1. Newey-West HAC t-stat > 2.0 | PASS |
| 2. OOS Sharpe > 1.0 (2023–2024) | PASS |
| 3. Monte Carlo CAGR > 0 (500 runs, 95th pct) | PASS |
| 4. Monte Carlo Sharpe shuffle range [1.749, 1.834] | PASS |
| 5. Bear market survival (2022) | PASS |
| 6. Slippage robustness (+0.2% cost overlay) | PASS |

---

## Per-Coin Survivor Status

| Coin | Status |
|---|---|
| BTC/USDT | SURVIVOR |
| ETH/USDT | SURVIVOR |
| SOL/USDT | SURVIVOR |
| BNB/USDT | SURVIVOR |
| AVAX/USDT | SURVIVOR |
| LINK/USDT | SURVIVOR |
| ADA/USDT | SURVIVOR |
| XRP/USDT | SURVIVOR |

---

## Portfolio Simulation

- Capital: $100,000 start
- Max concurrent: 3
- End capital: ~$1.28M
- Entry model: cap_at_open (correct concurrent sizing)

---

## Notes

- Signal SACRED — ADX=30, EMA 21/50/200, breakout=20, volume=2×
- No optimization performed post-validation
- Regime filter: per-coin EMA200 (Option B — no global BTC gate)
