---
title: Trading Guru Empire — Project Work Queue
type: project-work-queue
tags: [project, trading-guru-empire, queue]
status: active
updated: 2026-07-06
---

# Trading Guru Empire — Project Work Queue

This is the live execution queue for the project hub.

## Priority 1: Council automation

- Keep `Council_Runner_Automation` dry-run safe by default. Done: watcher fallback and signal path guards are now portable.
- Verify the battle-start trigger path end to end. Next: run one dry-run in the live repo and confirm `briefings/latest_signal.txt`.
- Keep the `.env` boundary explicit and never hard-code keys.

## Priority 2: War Room and Delegation

- Keep `War_Room_and_The_Delegation` aligned with the live repo structure. Done for the main note.
- Normalize the notes around the actual front-end and 3D playground ownership.
- Preserve the briefings-only contract for the councils.

## Priority 3: Research and reference hygiene

- Keep `OpenBB_Research` and `Free_APIs_Reference` as data/research support notes. Done: OpenBB now explicitly feeds the council signal bridge.
- Remove mirror noise only after a canonical copy is confirmed.
- Keep the project hub pointers in sync with the active repo. Done: `Trading_Guru_Empire_MOC` now points at `Project_Work_Queue`.

## Next checkpoint

1. Confirm the council runner still reflects the intended dry-run and cap guardrails.
2. Sync the remaining project notes with the live repo layout.
3. Start one concrete project task in the repo after the note map is settled.
