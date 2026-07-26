# 6-empires-os Audit & Deploy Log

## 2026-07-25 — RO-SUPREME-RUN

- Confirmed the canonical Mac Obsidian vault is `/Users/rolandgasparyan/Documents/Guru`.
- Confirmed the VPS services and local voice engine were active; public `/api/stt` and `/api/tts` were returning HTTP 404.
- Reviewed voice/deployment PRs #25, #26, and #27 plus the deployment hardening baseline PR #15.
- Repaired `empire-sync/sync-obsidian.sh` to use the canonical vault, `6-empires.com`, and an SSH identity fallback.
- Added managed Nginx exact routes for `/api/chat`, `/api/stt`, and `/api/tts` to the active port-8090 voice service.
- Added microphone recording/transcription and Armenian TTS playback controls to the current Next.js chat page.
- Repaired corrupted local Next SWC dependencies with `npm ci` from the lockfile.
- Verification: web typecheck passed; production build passed; deploy-script tests passed; shell syntax passed.
- Commit created: `b9985f5 Fix public voice routes and Obsidian sync`.
- Commit pushed to `origin/codex/durable-vps-obsidian-sync`.
- Production deployment was not forced: the VPS source checkouts remain drifted, so the controlled reconciler must reconcile the source checkout before activation.
- Voice retest: VPS-local TTS returned HTTP 200 and a valid 22050 Hz Armenian WAV; public TTS and STT both remained HTTP 404 because the pushed routes are not active in production.
- No repository reset, force push, secret output, or unsafe live production mutation was performed.
