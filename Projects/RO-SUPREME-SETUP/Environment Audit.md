# RO-SUPREME-SETUP Environment Audit

Audit date: 2026-07-25 (Asia/Yerevan)
Workspace: `/Users/rolandgasparyan/6-EMPIRES-OS`
Repository: `RolandGasparyan/6-empires-os`

## Executive result

The local development baseline is usable. Core tools are present, and the missing CLI tools were installed at user/tool level. The GitHub-VPS-Obsidian chain is only partially healthy: the real Mac vault is `/Users/rolandgasparyan/Documents/Guru`, while the legacy sync script points to the missing `/Users/rolandgasparyan/EmpireMemory/Obsidian_Second_Brain`. The VPS services are running, but its two repository checkouts are drifted and do not provide a safe deployment source of truth.

## Environment inventory

| Component | Result | Evidence |
|---|---|---|
| GitHub CLI | Partial | `gh 2.96.0` installed; local token reported invalid |
| Git | PASS | `git 2.50.1` |
| Node.js / npm | PASS | Node `v26.5.0`, npm `11.17.0` |
| Python / pip | Partial | Python `3.9.6`; `python3 -m pip` works, standalone `pip` is not on PATH |
| uv | PASS | `uv 0.11.25` |
| Docker | Partial | Docker `29.6.1`; daemon access requires the Docker Desktop/elevated runtime context |
| PM2 | Partial | Installed globally; default PM2 runtime directory needs a writable user context |
| Ruff | PASS | `0.16.0` |
| Bandit | PASS | `1.9.4` |
| pip-audit | PASS | `2.10.1` |
| ESLint | PASS | `10.8.0`; project lint still requires an ESLint configuration choice |
| Prettier | PASS | `3.9.6` |
| TypeScript | PASS | global `7.0.2`; project-local `5.9.3` used by typecheck |
| SSH | Partial | `~/.ssh/id_ed25519.pub` and `empire_github_sync.pub` exist; VPS SSH works through default identity/agent, but `~/.ssh/empire_vps` is absent |
| Obsidian vault | PASS | `/Users/rolandgasparyan/Documents/Guru`, 183 Markdown notes |
| Codex skills | PASS/Partial | Core project, GitHub, deploy, security, browser, and document skills are available; no missing task-critical skill was required |
| MCP/connectors | PASS/Partial | GitHub connector, browser/computer-use, node REPL, and Render MCP are available; GitHub Actions local `gh` access is blocked by stale auth/network |

## Verification evidence

- Local web typecheck: PASS.
- Python compilation for API, sync, deploy scripts: PASS.
- Deploy-script unit tests: 5 passed.
- Shell syntax checks: PASS for sync, reconcile, and VPS deploy scripts.
- Live `https://6-empires.com/`: HTTP 200.
- Live `https://6-empires.com/chat`: HTTP 200.
- Live `https://api.6-empires.com/health`: HTTP 200.
- Live frontend `/health`: HTTP 404; the API health route is on the API subdomain.
- Public `/api/stt` and `/api/tts`: HTTP 404.
- VPS localhost TTS: PASS, valid RIFF/WAV response.
- VPS localhost STT route: reachable, but empty audio produces an empty/error result as expected for the probe.
- VPS Piper binary and Armenian model: present.
- VPS `empire-ai`, `empire-sync`, and Docker services: active.

## GitHub voice/deployment PR review

- PR #27: `ci: add Empire chat repair workflow (audit + auto-fix)`. The proposed repair targets the old router/model failure mode and includes audit-only mode, backups, model probes, and STT/TTS verification.
- PR #26: `Add GitHub Actions workflow for automated voice chat fixes`. Dispatchable VPS workflow; its test plan still requires live verification.
- PR #25: `Enable automated Groq API key injection for voice chat deployment`. The stated STT verification and browser microphone test were not complete in the PR description.
- PR #24: legacy EMPIRE PRIME chat rollback.
- PR #15: broader authentication, persistence, CI, and deployment hardening baseline.

The current live result shows that the legacy `empire-ai-chat/server.js` has working local voice handlers, but the public `/chat` frontend is the newer Next.js app and its public host does not proxy `/api/stt` or `/api/tts`. This is the primary STT/TTS integration blocker.

## Live voice validation checklist

1. Open `https://6-empires.com/chat` in Chrome over HTTPS.
2. Confirm the microphone permission prompt is accepted and a physical input device is selected.
3. Record a short Armenian phrase and stop after the silence detector fires.
4. Success: the transcript appears in the chat input, with no `STT error` or `Didn’t catch that` message.
5. Send an Armenian chat request.
6. Success: a text response arrives and the speaker control produces audible Armenian audio.
7. Confirm browser DevTools Network entries for `/api/stt` and `/api/tts` are HTTP 200 with the expected JSON/audio content types.
8. Confirm the API/chat backend logs contain no provider, model, proxy, or timeout errors.

If STT fails, log: browser, OS, microphone device, permission state, recording MIME type, request URL, HTTP status, response body with secrets removed, timestamp, and the matching `empire-ai` journal lines.

If TTS fails, log: language, text length only (not private text), request URL, HTTP status/content type, audio byte count, browser playback error, and whether Piper, Azure, or eSpeak fallback was selected.

## Required follow-up

1. Choose one canonical source of truth for the vault and update the Mac sync path accordingly.
2. Choose one canonical VPS checkout; do not deploy while `/root/6-empires-os` and `/root/6-empires-os-full` remain drifted.
3. Route the live `/chat` API calls to the active voice service or implement the handlers in the current Next.js/API topology.
4. Re-authenticate `gh` before relying on local Actions logs.
5. Rotate any credential material found in VPS service configuration and keep secrets out of reports/logs.

No production deployment, repository reset, force push, or safety-gate change was performed by this audit.
