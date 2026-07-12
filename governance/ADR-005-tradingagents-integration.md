# ADR-005 — TradingAgents Integration

**Status:** DRAFT · 2026-05-21
**Layer:** Layer 1 (trading core) candidate · currently isolated to research sandbox
**Supersedes:** none
**Superseded by:** none

---

## Context

The operator has requested that [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) —
a multi-agent LLM-driven trading framework — be added to the repo "for
more extra trading Smart power."

This conflicts directly with several invariants the operator has
previously written into the system:

- **Strategy lock:** `STRATEGY_SHA256` pins a single strategy
  (`MA50W10`). The cinematic L3 disclosure repeatedly asserts: "All
  accounts execute the same SHA256-locked `MA50W10` strategy."
- **NO-DRIFT LAW:** "NO STRATEGY MUTATION · NO AUTONOMOUS EVOLUTION ·
  NO GOVERNANCE BYPASS" — printed by `ops/command-center.sh`.
- **Single-source executor:** `canary/canary_executor.py` is the only
  live-order path, and it executes `canary_strategy.py` deterministically.
- **Strategy integrity watcher:** `canary/watch_strategy_integrity.sh`
  actively guards against unauthorized strategy changes.

A live-execution integration of TradingAgents would replace or augment
that single-strategy contract with LLM-driven decisions, which
contradicts every one of the bullets above. This ADR exists so that any
such change is reviewed deliberately rather than landing as a drive-by
commit.

---

## Decision (draft)

Adopt a **three-phase**, opt-in approach. Phase 1 is what landed with
this ADR. Phases 2 and 3 each require their own follow-up ADRs and
operator sign-off.

### Phase 1 — Isolated research sandbox (active)

- TradingAgents lives at `research/tradingagents/` as a **pinned git
  submodule** (currently `61522e1`).
- Has **no** access to live API keys.
- Has **no** order-execution path.
- Is **not** imported by `canary/`, `arena_shadow_runner.py`, or any
  systemd-managed process.
- Is **not** referenced by `ops/command-center.sh` GUARDED ZONE
  subcommands.
- Documentation (`research/README.md`) explicitly states the boundary.

Phase 1 changes nothing about how live trades are made. It is a
read-only research artifact.

### Phase 2 — Paper / sim evaluation (NOT YET AUTHORIZED)

Conditions that would gate Phase 2:

- A separate ADR-006 specifying:
  - Which paper/sandbox exchange is used.
  - How TradingAgents config is parameterized (model, prompts, tools).
  - Capital ceiling, position size limits, and a hard daily loss limit
    enforced in the paper executor.
  - How TradingAgents output is logged and audited.
  - A rollback plan: how to disable the paper integration in one
    command.
- A dedicated paper account with **no** live keys configured.
- A `PAPER_AGENT_DECISIONS=YES` env flag plus a CONFIRM-style operator
  gate analogous to `CONFIRM=YES`.
- A minimum evaluation window (proposed: 30 days of paper trades) with
  measurable success criteria defined in advance.

### Phase 3 — Gated live integration (NOT YET AUTHORIZED)

Conditions that would gate Phase 3:

- A separate ADR-007 explicitly amending or retiring:
  - `STRATEGY_SHA256` lock (or extending it to cover an agent config
    hash).
  - The "All accounts execute the same SHA256-locked `MA50W10`
    strategy" disclosure.
  - The NO-DRIFT LAW wording in `ops/command-center.sh`.
- Phase 2 must have produced evidence supporting integration, reviewed
  by the operator.
- A new `LIVE_AGENT_DECISIONS=YES` env flag, distinct from existing
  gates, with its own CONFIRM step per-session.
- Strict per-trade audit log entries (model, prompt hash, decision,
  fills) written to `battle.log`.
- A kill-switch wired so the existing `protection_halt.json` and
  `CANARY_HALT.json` files immediately disable agent-driven decisions
  in addition to halting the strategy executor.
- Position size limits enforced **before** the agent layer can issue
  an order, not after.

Until Phase 3's ADR is merged, **no** code path in this repo should
call into `research/tradingagents/` from a live-execution context. Any
PR that attempts to wire TradingAgents into `canary_executor.py`,
`arena_shadow_runner.py`, or any systemd service must be rejected
pending Phase 3 sign-off.

---

## Consequences

### Phase 1 (in effect now)

- ✅ The operator has the toolkit available locally for experimentation.
- ✅ No change to live trading behaviour, governance, or strategy lock.
- ✅ Pin is updateable via normal PR.
- ⚠️ Sandbox dependency footprint is not yet audited; treat its
  requirements file as untrusted until reviewed.
- ⚠️ Operator must self-discipline: do not source live exchange keys
  into a venv used to run research/tradingagents/.

### Phase 2 and 3 (deferred)

- 🛑 Live execution under this framework is **not authorized** by this
  ADR.
- 🛑 Any cinematic claim that the championship is "real LLM agents
  competing" while phases 2/3 are unauthorized must be paired with the
  cinematic-layer disclosure that the underlying strategy is still
  `MA50W10`.

---

## Open questions

1. Does the operator want Phase 2 in scope at all, or is Phase 1
   (sandbox research) sufficient?
2. If Phase 2 is in scope, which paper venue?
3. What is the kill-criterion for the paper evaluation — what
   PnL/Sharpe/DD profile would fail Phase 2 and stop it from
   progressing to Phase 3?
4. How is model output cached / audited so a regulatory or
   post-incident review can reconstruct exactly what the model saw and
   said at each decision point?
5. Does the cinematic disclosure language need to evolve even at Phase
   1 (e.g., "All live accounts execute MA50W10; research/ contains
   isolated unrelated frameworks")?

---

## References

- `research/README.md` — sandbox boundary.
- `research/tradingagents/` — pinned submodule
  (`https://github.com/TauricResearch/TradingAgents`).
- `canary/canary_strategy.py` — current sole live strategy.
- `canary/watch_strategy_integrity.sh` — integrity watcher.
- `ops/command-center.sh` — NO-DRIFT LAW banner; GUARDED ZONE; SAFE
  ZONE; L3 disclosure.
- `governance/AI_DISCIPLINE_CONSTITUTION.md` — discipline framework.
- `governance/BRANCH_LOCK.md` — branch governance.
