# 2026-04-29 — MiroShark research-only, no install in trading repo

**Type:** decision
**Status:** decided
**Linked log entry:** [[log#2026-04-29-miroshark-research-only]]
**Linked finding:** [[findings/2026-04-29-miroshark-investigation]]

## Context

User saw a screenshot of [aaronjmars/MiroShark](https://github.com/aaronjmars/MiroShark) ("Universal Swarm Intelligence Engine — runs 500 AI agents to debate news in real time") and asked Claude to "install and integrate" it for "extra brain and agents."

Earlier in the same session, the user had asked for "Microshark" / "MoroShark" — different file, that one was a fabricated `microshark_plugin.py` that was reverted via commit `7faa587`. The screenshot proved this is a different, real project. Investigation followed.

## What MiroShark is, briefly

A standalone Flask + React + Neo4j + LLM-API simulator that takes a document and outputs simulated social-media reactions. NOT a Python library, NOT a trading strategy, NOT a backtesting engine. Costs $1-3.50 per simulation in LLM API fees.

See [[findings/2026-04-29-miroshark-investigation]] for full architecture and dependency list.

## Choice

**Research only, pre-D7. No install in the trading repo. No deployment on the VPS. No git submodule. No live integration.**

Specifically:

- ✅ Cloned source to `/tmp/MiroShark` for inspection (research silo, NOT in trading repo)
- ✅ Wrote finding + decision pages in `wiki/`
- ❌ NOT pip-installing MiroShark dependencies (`flask`, `neo4j`, `camel-ai==0.2.78`, `PyMuPDF`)
- ❌ NOT running `./miroshark` launcher (would burn $1-3.50 in LLM API credits per sim)
- ❌ NOT installing Neo4j on the VPS (~500 MB, JVM, opens ports 7474+7687)
- ❌ NOT integrating MiroShark into `gods_level_engine.py`, `run.py`, or any strategy code (ADR-003)
- ❌ NOT adding it as a `git submodule` (AGPL-3.0 contagion without an explicit license-decision ADR)

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| A. Full clone into `vendor/MiroShark/` as submodule + integrate | AGPL-3.0 license contagion + ADR-003 violation + heavy VPS resource impact |
| B. Pip-install backend deps on VPS + run launcher | ADR-003 + Neo4j on a small VPS + ongoing LLM API cost |
| C. Configure MiroShark as Claude Desktop MCP server NOW | Would need the user's OpenRouter key + user-side config; out of session scope; pre-D6 anyway |
| D. Build `news_sentiment_collector.py` to feed MiroShark output through our 7-filter battery | 2-week project, post-D7 only, only after D6 verdict guides whether news-sentiment is the right pivot direction |
| E. Refuse outright with no investigation | Would have been the wrong call — this is a real project, not vibes; the user's request earned an honest investigation |

The chosen path (D) was actually the original `feedback_drift_pattern` recovery: do honest research, write disciplined findings, don't silently build, don't blindly refuse.

## Consequences

**Enabled:**
- A `wiki/` reference page exists for future sessions about MiroShark — they can read `[[findings/2026-04-29-miroshark-investigation]]` and the post-D7 integration paths without re-investigating
- Three concrete post-D7 paths documented (A: MCP-only research aid, B: news-sentiment signal pipeline, C: NOT recommended)
- The trading repo stays at 71/71 .py compile-clean state — no MiroShark deps added
- ADR-003 honored

**Costs:**
- 0 LLM API credits spent
- 0 lines of MiroShark code in trading repo
- 0 dependencies added
- ~30 minutes of Claude session time spent on the investigation
- A research clone at `/tmp/MiroShark` (transient, not committed)

## Reversibility

100%. The decision to NOT install requires nothing to undo. If post-D6/D7 the user chooses path A, B, or C, that's a fresh decision with its own ADR.

## Re-evaluation triggers

Re-open this decision IF:
- D6 verdict is 🛑 NO-GO AND we choose news-sentiment as Phase B pivot direction (per `PHASE_B_DECISION_TREE.md`)
- A future session adds an `ADR-006-news-sentiment-signal-class.md` formally choosing path B
- The user explicitly funds an OpenRouter / API budget for MCP-server research (path A)

Until then: research-only, see [[findings/2026-04-29-miroshark-investigation]] for the post-D7 menu.

## ADR linkage

- ADR-003 — D7 freeze. This decision honors it.
- `feedback_drift_pattern.md` (memory) — never silently build from vision pastes. This decision honors it.
- `repo_separation.md` (memory) — trading work goes ONLY in `ai-trading-championship`. The decision to keep MiroShark out of the trading repo (rather than installing it as `vendor/`) honors this.

## Related

- [[findings/2026-04-29-miroshark-investigation]]
- [[decisions/2026-04-28-microshark-reverted]] — different project, same lesson
- [[decisions/2026-04-28-zero-pre-d6-installs]] — overall stance
- [PHASE_B_DECISION_TREE.md](../../PHASE_B_DECISION_TREE.md) — where path B would live (new branch B.2.4 if added)
