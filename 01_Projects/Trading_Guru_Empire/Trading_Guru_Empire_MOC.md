---
title: Trading Guru Empire — MOC
type: project-moc
tags: [project, trading-guru-empire, moc]
status: active
updated: 2026-06-08
---

# 🏛 Trading Guru Empire — Map of Content

The trading-championship empire: shadow battles, AI councils, strategy R&D, and supporting infra. Repo lives at `~/tradingguru-empire/`.

## Pillars
- [[Councils_28]] — the 28 AI agent teams (The Delegation) + the 11-point Trading Constitution
- [[Council_Runner_Automation]] — councils auto-brief **when a battle starts** (headless, capped, dry-run safe)
- [[Free_APIs_Reference]] — 147 free crypto/finance/blockchain APIs (from public-apis)
- [[War_Room_and_The_Delegation]] — the pixel War Room UI + the 3D agent playground

## Strategies (Areas)
- [[MA50W10_Strategy]] — validated setup
- [[RSI2_Champion_Cell]]
- Evidence: [[MA50W10_Backtest_Evidence]] · [[GODSMODE_Research_Results]]

## The 11-Point Trading Constitution
1. Capital Preservation First
2. Risk-Adjusted Decisions
3. No Emotional Trading
4. No Narrative Attachment
5. No Token Loyalty
6. No FOMO
7. No Revenge Trading
8. Expected Value Over Opinion
9. Every Decision Must Be Explainable
10. Every Decision Must Be Auditable
11. Survival Before Growth

## Battle lifecycle (verified)
- Start: `start_shadow_round.sh` → writes `runtime/shadow_round.pid` (`LIVE_ORDERS=0`, shadow only)
- Stop: `stop_shadow_round.sh`
- On start, [[Council_Runner_Automation]] fires the councils.

> [!note] Live trading
> Shadow / paper only here. No live order execution is wired, and the councils produce **briefings, never trades**.
