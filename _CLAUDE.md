# _CLAUDE.md — Operating Manual for Obsidian_Second_Brain

> This file is the operating manual for **this vault**. Every Claude session that starts
> here reads this FIRST. It overrides skill defaults on vault-specific rules.
> Generated 2026-06-17 from a live audit. See `00_Meta/Vault_Map.md` for vault-of-vaults context.

---

## 0. AI-first rule

Every note is written for future-Claude to read and reason over. Keep notes self-contained,
frontmatter-first, with `[[wikilinks]]` to every person/project/strategy mentioned, and a
source URL inline for any external claim.

---

## 1. ⚠️ Canonical scope — what IS and ISN'T the vault

This folder currently contains **two things tangled together**. Only the first is the vault.

### ✅ THE VAULT (canonical — read, write, maintain these)
PARA structure + the home dashboard:

| Path | Purpose |
|---|---|
| `00_Home.md` | Dashboard / entry point |
| `00_Meta/` | Vault map, system authority, founder OS, knowledge audits |
| `01_Projects/` | Active projects (e.g. `Trading_Guru_Empire/`) + daily notes |
| `02_Areas/` | Ongoing areas — `AI_Models/`, `Infrastructure/`, `Trading_Strategies/` |
| `03_Resources/` | Reference — `Backtests/`, `External_Links/` |
| `04_Archives/` | Archived material (currently empty) |
| `99_Templates/` | Note templates (`{{date}}` placeholders) |

### 🚫 NOT THE VAULT (a trading-code repo dumped on top — IGNORE for vault ops)
A full app repo (`.gitignore` header: *"canary trading agent + React/Vite championship app"*)
was merged into this folder. **Do not treat these as second-brain notes.** Do not edit them as
notes, link to them, or count them in vault health. They are the source of ~745 of the vault's
773 known structural issues (orphans, broken links, missing frontmatter, duplicates).

- **~50 lowercase dirs**: `bot/ server/ client/ dashboard/ docs/ governance/ SecondBrain/`
  `second-brain/ production_engine/ canary/ design/ intelligence/ l99/ l99_bot/ research/`
  `strategies/ scripts/ src/ tests/ backups/ audit/ ops/ champion/ godmode/` … and more.
- **64 loose root files**: `CLAUDE.md` (the code repo's guide), `AGENTS.md`, `README.md`,
  `CHANGELOG.md`, `SECURITY.md`, all `D6_*`, `GODMODE_*`, `CHAMPION*`, `*_RESULTS.*`,
  `*_SWEEP_*`, `requirements*.txt`, `replit*`, `QUARANTINE_PLAN_*.txt`, etc.
- A git submodule (`research/tradingagents`, currently uninitialized).

> The code's real home is the dedicated repos (`ai-l99-production`, `tradingguru-agent`),
> not this vault. A quarantine/removal decision is the operator's to make — never auto-move
> or auto-delete. `QUARANTINE_PLAN_20260608T175139Z.txt` already exists at root.

When the operator decides to separate them, that is a destructive structural change → present
an ACTION PLAN and get explicit approval first.

---

## 2. Naming conventions

- **Notes**: `Title_With_Underscores.md` (e.g. `MA50W10_Strategy.md`, `Trading_Guru_Empire_MOC.md`).
  NOT the `YYYY-MM-DD — Title` skill default.
- **Daily notes**: `YYYY-MM-DD.md` (e.g. `01_Projects/2026-06-17.md`). No dedicated `Daily/`
  folder exists yet — they currently land in `01_Projects/`. Confirm placement with operator
  before standardizing.
- **MOCs**: suffix `_MOC.md`, frontmatter `type: project-moc`.
- No special characters except `_` and `—` (em dash). Avoid spaces in new note filenames.

---

## 3. Frontmatter schema

Inline-array tags (not block lists). Match the existing style exactly:

```yaml
---
title: Human Readable Title
type: dashboard | meta | project | project-moc | area | resource | strategy | daily
tags: [moc, home]          # inline array
status: active | planning | completed | archived | on-hold   # projects only
priority: high | medium | low                                 # projects only
updated: 2026-06-17        # evergreen notes
date: 2026-06-17           # dated/daily notes
---
```

Templates live in `99_Templates/` and use `{{date}}`:
`Daily_Note_Template.md`, `Project_Note_Template.md`, `Trading_Strategy_Template.md`.

---

## 4. Active project

- **[[Trading_Guru_Empire_MOC|Trading Guru Empire]]** — `01_Projects/Trading_Guru_Empire/`
  - Pillars: `[[Councils_28]]`, `[[Council_Runner_Automation]]`, `[[Free_APIs_Reference]]`,
    `[[War_Room_and_The_Delegation]]`
  - Strategies (Areas): `[[MA50W10_Strategy]]`, `[[RSI2_Champion_Cell]]`
  - Evidence (Resources): `[[MA50W10_Backtest_Evidence]]`, `[[GODSMODE_Research_Results]]`
  - This vault documents **shadow/paper** work only; the MOC notes live trading is **not** wired here.

---

## 5. Write rules (propagation)

When creating/updating a note, also update where it belongs:
- New project → `00_Home.md` "Active project" list + its MOC.
- Strategy → `02_Areas/Trading_Strategies/` + link evidence in `03_Resources/Backtests/`.
- Anything structural → note it in `00_Meta/`.

Search before creating (the vault already has heavy duplication from the dump — don't add more).
Match the voice of existing notes in the same folder before writing.

---

## 6. Safety / discipline (inherits operator's global rules)

- **Default read-only.** Present an ACTION PLAN before any move/delete/structural change.
- **Never auto-delete or auto-move.** Nothing in `.trash/` or the code dump is touched without
  explicit, per-item operator approval.
- **No financial actions.** This vault is documentation/observability only — never trigger
  trades, logins, or live operations from here.
- **Secrets**: this folder is git-tracked AND iCloud-synced. If a key/token is ever spotted in a
  note, warn and tell the operator to rotate — never echo it back. Run a `gitleaks` history scan
  before pushing.

---

## 7. Known cleanup backlog (read-only findings, 2026-06-17 audit)

- Empty stray notes: `2026-06-07.md` (root), `01_Projects/2026-06-17.md`,
  `01_Projects/Безымянная Kanban-доска.md` ("Untitled Kanban board").
- Empty folders: `02_Areas/Architecture/`, `03_Resources/Market_Data/`, `04_Archives/`,
  `Untitled/`, `trading-guru-empire/`, `research/tradingagents/`.
- The code-dump quarantine (Section 1) — operator decision pending.
- No vault `index.md` / `log.md` yet (skill expects them) — create if adopting full skill workflow.
