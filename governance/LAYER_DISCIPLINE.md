# Layer Discipline — Immutable

## Layer 1 — Trading (LOCKED at design time)

- The ONLY validated edge: **MA50W10** (Sharpe 2.81, +3,427% backtest)
- Strategy file: /root/agent/canary/canary_strategy.py
- SHA256 lock: 704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143
- Capital cap: $100 USDT (separate sub-account, NOT main keys)
- Lifetime cap: 48h per arm cycle
- Loss cap: $2.00 max acceptable
- Mutations require: design-time review, NOT runtime hot-patch

## Layer 2 — Telemetry

- Read-only. Pulls from terminal.json, no exchange writes.
- Live services: tradingguru-telemetry, tradingguru-bots-updater, microstructure-collector
- Never executes orders.

## Layer 3 — Cinematic (free-form)

- Frontend at /var/www/ai-trading-championship/
- ChampionshipOverlay, RivalryPanel, DetailedStats, CyclePanel
- Zero coupling to Layer 1.
- Can be rewritten freely without touching Layer 1.

## The three rules

1. **Layer 1 mutations need design-time approval + SHA256 lock rotation.**
   Never edit live code, never hot-patch parameters.
2. **Layer 2 is read-only.** If you find yourself writing to terminal.json from a trading process, you violated Layer 2.
3. **Layer 3 cannot reach Layer 1.** Frontend cannot trigger trades. Period.

## Refused drift patterns (see 9-refusals-log.md)

- GODMODE multi-pair rotation (math fails)
- Self-evolving live trading (no edge proven)
- Parameter mutations on locked strategies
- Bypassing canary phase

## Memory.md cross-refs

- feedback_drift_pattern.md — operator waives own guardrails under pressure
- repo_separation.md — trading work ONLY in /root/agent/ (server) and ~/Desktop/agent/ (local)
