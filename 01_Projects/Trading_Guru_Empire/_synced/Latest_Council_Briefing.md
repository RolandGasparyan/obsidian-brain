# Latest Council Briefing

Mirror snapshot of the most recent council-runner output.

- Source briefing: `council_runner/briefings/briefing-2026-07-06T16-42-28-915Z.md`
- Signal bridge: `council_runner/briefings/latest_signal.txt`
- Mode: `DRY-RUN` for the briefing pass, then live-style signal generation from OpenBB + Kronos
- Status: clean dry-run path, no spend, no trades

## What this run confirms

- Watcher trigger fires on battle-start PID changes.
- Council runner writes fresh briefings in dry-run mode.
- OpenBB → Kronos signal bridge writes `latest_signal.txt` and per-symbol signal notes.
