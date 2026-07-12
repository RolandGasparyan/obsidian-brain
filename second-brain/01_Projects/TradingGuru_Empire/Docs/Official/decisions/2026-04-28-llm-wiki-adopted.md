# 2026-04-28 — Adopt Karpathy LLM Wiki pattern

**Type:** decision
**Status:** decided
**Linked log entry:** [[log#2026-04-29-1500-decision-adopt-karpathy-llm-wiki-pattern]]

## Context

User asked Claude to "find Karpathy's Obsidian RAG and install and setup to my project and run." The phrase "Obsidian RAG" wasn't a project Claude immediately recognized; Karpathy's famous repos are nanoGPT, llm.c, llama2.c, etc. Investigation needed.

## Investigation

Web search revealed: Karpathy published a [GitHub gist on 2026-04-03](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) titled "llm-wiki" describing an architecture pattern, NOT a software package. Multiple community implementations followed (Ar9av/obsidian-wiki, AgriciDaniel/claude-obsidian, etc.).

The pattern explicitly **rejects vector databases** for project-sized knowledge bases. Instead: markdown files + folder structure + LLM reading directly via context window. Three layers: raw sources → wiki → schema.

## Choice

Adopt the pattern in this trading repo, **minimally**:

- Add `wiki/` folder with `schema.md`, `index.md`, `log.md`
- Add `wiki/concepts/`, `wiki/decisions/`, `wiki/findings/` subdirs
- Existing research markdown at repo root (`CHAMPION.md`, `PHASE_B_DECISION_TREE.md`, `D6_DRYRUN_*`, etc.) **stays in place** — wiki references via wikilinks/markdown links
- No external implementation cloned, no `bash setup-vault.sh` run, no Obsidian app required
- Schema co-developed with Claude (per Karpathy's recommendation)

This is **Option 3** of the AgriciDaniel/claude-obsidian setup options: "Copy the pattern instructions, paste into Claude, organize markdown."

## Alternatives considered

| Alternative | Rejected because |
|---|---|
| A. Clone AgriciDaniel/claude-obsidian as a Claude Code plugin | Adds plugin dependency + Obsidian app; over-engineering for our use case |
| B. Clone Ar9av/obsidian-wiki | Designed for general AI agents, not Claude-Code-specific; less integrated |
| C. Build vector RAG with embeddings | Karpathy's whole point: vector DBs over-engineer mid-sized knowledge bases. Our project is small enough to live in context. |
| D. Don't adopt anything | Wastes the existing research markdown ecosystem; doesn't help future-session continuity beyond what `CLAUDE.md` already provides |

## Consequences

**Enabled:**
- Future Claude sessions get an indexed catalog (`wiki/index.md`) instead of grepping for filenames
- Append-only log (`wiki/log.md`) preserves session-by-session decisions
- Atomic concept pages (`wiki/concepts/*.md`) deduplicate explanations across docs
- Decisions and findings pages give **structured archives** of "why we did/didn't do X"

**Costs:**
- ~10 markdown files to create initially
- Maintenance discipline required: append to log, don't edit past entries
- Index requires periodic regeneration (manual now; could be auto-scripted post-D7)

## Reversibility

100% reversible. To undo: `rm -rf wiki/`. No code depends on it; no scripts read from it. It's pure documentation organization. The wiki is a SUPERSET of the existing markdown — removing it loses no information.

## ADR linkage

Does NOT violate ADR-003 (no new strategy code on `main`). The wiki contains zero Python; only markdown. The decision to adopt the pattern is itself a documentation-organization choice, not a strategy choice.

## Related

- [Karpathy's gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — original pattern
- [VentureBeat coverage](https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an) — context
- [[schema]] — project conventions on top of the abstract pattern
- [[log#2026-04-29-1500]] — log entry
