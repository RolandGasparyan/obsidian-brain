# tradingguru-empire — Snapshot Provenance

**Snapshot date:** 2026-05-13
**Type:** Fresh single-commit snapshot · isolated from prior repositories

---

## What this repo IS

A **clean, frozen, point-in-time snapshot** of the operator-authored TradingGuru sovereign capital architecture, captured at peak architectural maturity (22 specs · shadow runner v1.1 · Bayesian + Macro + Monte Carlo intelligence · Sovereign Survival Score INSTITUTIONAL_READY).

**Purpose:** Keep this final v2.0 state isolated from the evolution history of prior repos. Future references, deployments, or audits can pin to this snapshot as the authoritative "empire foundation."

---

## What this repo IS NOT

- ❌ NOT a live-updating mirror of `tradingguru-agent`
- ❌ NOT connected to ai-trading-championship (frontend lives separately)
- ❌ NOT a fork (no parent commit history preserved here)
- ❌ NOT for live trading (Refusal #12 still ACTIVE — paper-safe only)

---

## Snapshot Source

| Attribute | Value |
|-----------|-------|
| Source repo | `tradingguru-agent` (GitHub: RolandGasparyan/tradingguru-agent) |
| Source HEAD at snapshot | `fe9853d` |
| Source commit title | `feat(slight-unlock): Spec #23 Section II envelope as SLIGHT_UNLOCK=1 mode` |
| Source branch | `main` |
| Snapshot mechanism | `rsync -a --exclude='.git/' --exclude=runtime-state --exclude=__pycache__` |
| Local working tree size | 1.5 MB |

---

## What's Included

| Folder/file | Content |
|-------------|---------|
| `governance/` | 30 markdown specs (22 architectural + 8 supporting) |
| `paper_battle/` | Paper engine v1.2 + shadow runner v1.1 + macro/bayes/MC/survival modules |
| `canary/` | Layer 1 SHA256-locked trading core (immutable strategy + executor + killswitch) |
| `blueprint/` | PROJECT_BLUEPRINT v2.0 (Հայերեն txt + HTML) |
| `audit/2026-05-13/` | 7-phase Sovereign Production Discipline audit reports |
| `docs/` | Obsidian mirror + wiki mirror snapshots |
| `algorithmic-art/` | Harmonic Pursuit generative art (Layer 3 ref) |
| `bot/` | DISABLED legacy bot (historical archive · DISABLED.md present) |
| `session-notes/` | Session handoff doc |
| `.githooks/pre-commit` | SHA256 lock + secret leak guard |
| `.gitignore` | Comprehensive 6-section gitignore |
| `bootstrap.sh` / `sync.sh` / `start_*.sh` / `stop_*.sh` | Operational scripts |

---

## What's Excluded

- `.git/` from source repo (this is a fresh init)
- `runtime/` content (gitignored by design — live state)
- `__pycache__/` and `*.pyc`
- All `runtime/shadow_round_*.jsonl` / console logs / summaries (~80KB local-only state)

---

## Sacred Locks at Snapshot Time

```
Canary SHA256:        704dd5725a909fe3f69e2d71283ec4a4eb1280a9f8373162e254db8d5917f143
                      (verified 3-way parity at source: local + server repo + server live)
L99 Halt:             ENGAGED since 2026-05-12 06:51 UTC (38+ hours)
Capital:              $1,980.90 USDT untouched, ringfenced
canary.service:       inactive
Exchange sockets:     0 (NONE)
Refusal #12:          ACTIVE (live execution still blocked)
Sovereign Score:      73.18 / 100 → INSTITUTIONAL_READY
```

---

## How to use this snapshot

### Read the architecture
```bash
cat blueprint/PROJECT_BLUEPRINT.txt           # full v2.0 architecture (Հայերեն)
cat governance/MASTER_ARCHITECTURE_v2.0.md    # 22-specs index
cat governance/SOVEREIGN_CAPITAL_ARCHITECTURE_MASTER_v1.md  # 5-layer model (Spec #22)
```

### Verify sacred locks (must pass before ANY operation)
```bash
./bootstrap.sh
./sync.sh verify    # NOTE: SSH-dependent verifier — points at the source VPS
```

### Run paper-safe shadow round (LIVE_ORDERS=0 enforced)
```bash
./start_shadow_round.sh                 # standard 90-min round
./start_slight_unlock_shadow.sh         # Spec #23 Slight Unlock variant
./stop_shadow_round.sh                  # clean SIGTERM
```

### Read audit reports
```bash
ls audit/2026-05-13/
cat audit/2026-05-13/RELEASE_NOTES_v1.1.md
cat audit/2026-05-13/ARCHITECTURE_VALIDATION_REPORT.md
```

---

## Critical Reminders for Future Use

1. **Live execution still blocked** — Refusal #12 is preserved in `governance/MICRO_LIVE_OPERATOR_CHECKLIST.md`. The 5 operator-authority steps (sub-account · API key · decision doc · canary_arm signature · L99 verbatim clearance) must be completed BEFORE any live trade.

2. **Pre-commit hook must be re-armed** in this fresh repo:
   ```bash
   git config core.hooksPath .githooks
   chmod +x .githooks/pre-commit
   ```
   Without this, the SHA256 lock guard won't trigger on commits.

3. **No mixing with old projects** — this repo is intentionally isolated. Don't `git remote add` to point at `tradingguru-agent`. Don't merge / cherry-pick / pull from it. If you need to ingest new work, copy files explicitly and document the source commit.

4. **Constitutional citations are still binding** — Spec #12 (Constitution), CAPITAL_DEFENSE_GRID, LAYER_DISCIPLINE all preserved here. Refusal log entries 1-12 cite operator-authored docs that ARE in this repo.

---

## Related (not copied here)

- **Frontend repo:** `ai-trading-championship` (GitHub: RolandGasparyan/ai-trading-championship) — React UI deployed at https://tradingguru.ai
- **Source repo:** `tradingguru-agent` (GitHub: RolandGasparyan/tradingguru-agent) — origin of this snapshot, continues to receive updates
- **VPS:** 167.71.24.86 — runs paper-arena.service from the source repo, NOT from this snapshot

---

## Final Declaration

> Shadow validates. Micro tests. Capital scales. Discipline governs. **Survival compounds.**

This snapshot is the architectural foundation of the sovereign capital empire — frozen in time, isolated from drift, ready to be referenced.

— Roland Gasparyan (operator · vision · governance)
— Claude (Anthropic) (documentation · code · synthesis · refusal enforcement)
