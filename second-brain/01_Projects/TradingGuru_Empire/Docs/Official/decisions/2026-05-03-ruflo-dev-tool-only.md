# 2026-05-03 — Ruflo dev-tool only, NOT in trading loop

**Type:** decision
**Status:** decided
**Linked log entry:** [[log#2026-05-03-ruflo-dev-tool-only]]
**Linked finding:** [[findings/2026-05-03-ruflo-investigation]]

## Context

User showed a GitHub feed screenshot featuring three repos (NTSB FOIA docs, TauricResearch/TradingAgents, sammchardy/python-binance) and asked to "integrate" them for "more power." After pushback, user provided a fourth repo URL — [ruvnet/ruflo](https://github.com/ruvnet/ruflo) — and asked again to "make more agentic power of this project."

The discipline-framework hard rule (`CLAUDE.md` rule #3) flags repeated "more power" / "next step" requests as a known drift pattern, so investigation came first. See [[findings/2026-05-03-ruflo-investigation]].

## What Ruflo is, briefly

Agent orchestration platform — Claude Code plugin + MCP server + npm CLI — for coordinating swarms of dev-workflow agents (code review, testing, security audit, documentation). MIT-licensed, 37.1k stars, mature. **Not** a trading framework; ships zero signal generators, zero exchange adapters, zero backtesting.

Hard deps: Node.js + MongoDB. Optional: Ollama/vLLM, Neo4j.

## Choice

**Conditionally accept Ruflo as a developer-machine tool only. Reject any integration into the trading loop, the VPS, or strategy code.**

Specifically:

- ✅ User MAY install on their dev machine via `/plugin install ruflo-core@ruflo` or `claude mcp add ruflo`
- ✅ User MAY use Ruflo agents to assist with code review, test coverage, wiki lint, security audit of `bot-control` HTTP endpoints
- ✅ This decision page + finding page committed to `wiki/` for future-session reference
- ❌ NOT installing Ruflo on the VPS (167.71.24.86) — Node + MongoDB on a box already running 4 bots + collector + 2 timers is unjustified
- ❌ NOT adding Ruflo agents as voters in `gods_level_engine.py` or any vote ensemble
- ❌ NOT calling Ruflo from `run.py`, `backtest.py`, or any strategy code
- ❌ NOT adding `ruflo` as an npm dependency to this repo (this repo is Python; no `package.json`)
- ❌ NOT using Ruflo's GOAP planner or autonomous agents to make trade decisions
- ❌ NOT spending LLM API budget on per-trade agent calls (would dwarf the 30 bps fee gate that already failed D6)

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| A. Wire Ruflo agents into the vote ensemble | Replays the 9-agent ensemble that returned −0.5% / 24mo per `MA_STRATEGY.md`. More agents was already proven not to be the bottleneck. |
| B. Run Ruflo on the VPS as an autonomous trading agent | ADR-002 says Phase B direction is on-chain B1 (different signal class), not multi-agent on the same failed class. Plus Node + MongoDB on the small VPS. |
| C. Add `ruflo` as a git submodule under `vendor/` | This repo is Python; no JS toolchain. License is fine (MIT) but the integration cost is unjustified for a non-trading tool. |
| D. Use Ruflo agents to *generate* strategy code, then commit | The 2026-04-28 reverts (microshark + Sprints 2-14, 17 commits) prove unverified AI-generated commits become a liability. Hard rule #1 of `CLAUDE.md`. |
| E. Refuse outright with no investigation | Same mistake as a blind yes — the user's request earned an honest investigation, especially after they provided the actual URL. |
| **F. Conditional accept as dev-machine plugin only** ← chosen | Honors ADR-002, ADR-003 spirit, hard rule #3, repo-separation memory. Zero trading-code impact. 100% reversible. |

## Consequences

**Enabled:**
- User has a documented path to use Ruflo for dev productivity if they want it
- Future sessions reading [[findings/2026-05-03-ruflo-investigation]] will not re-investigate
- Clear precedent that "MIT license + Claude Code plugin manifest" is necessary but not sufficient — the *category match* matters more
- Branch `claude/integrate-recommendations-XVgTr` lands disciplined documentation rather than speculative code

**Costs:**
- 0 lines of Ruflo code in trading repo
- 0 dependencies added to `requirements.txt`
- 0 changes to VPS services
- 0 LLM API spend
- ~20 minutes of session time on the investigation + write-up

## Reversibility

100%. Nothing was installed in the trading repo or on the VPS. If post-D7 the user later chooses a different shape (e.g. specific MCP-based dev assist), that is a fresh decision with its own ADR.

## Re-evaluation triggers

Re-open this decision IF:

- The user wants a formal `ADR-005-dev-tooling-policy.md` defining which Claude Code plugins are sanctioned for the project
- A specific Ruflo-shipped agent (e.g. the security-audit agent) is needed for a concrete task — at which point the decision narrows to "use that one agent for that one task," not "integrate the whole platform"
- Phase B direction shifts to a multi-agent reasoning class (currently B.2.3 = on-chain B1; not multi-agent)

## ADR linkage

- ADR-002 — Phase B direction (microstructure first → on-chain B1 fallback). This decision honors it; Ruflo is not on the B-tree.
- ADR-003 — D7 freeze. Freeze expired 2026-05-01, but the spirit (no untested strategy code on `main`) still applies. This decision adds zero strategy code.
- `feedback_drift_pattern.md` (memory) — "more power / next step" requests are known drift cues. Investigation + disciplined write-up is the documented recovery.
- `repo_separation.md` (memory) — trading work goes only in `ai-trading-championship`. This decision keeps Ruflo *out* of the trading repo.

## Related

- [[findings/2026-05-03-ruflo-investigation]]
- [[decisions/2026-04-29-miroshark-research-only]] — direct precedent
- [[decisions/2026-04-28-microshark-reverted]] — what happens when investigation is skipped
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — actual next step (B.2.3 on-chain B1)
- [MA_STRATEGY.md](../../MA_STRATEGY.md) — empirical "more agents ≠ more edge"
