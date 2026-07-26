# RO-SUPREME-SETUP Environment Audit

Audit date: 2026-07-26 (Asia/Yerevan)

## Executive result

The local empire workflow is operational for GitHub, Git, Node.js, Python, Docker, PM2, security tooling, Codex, Claude Code, Obsidian, SSH, and the verified DigitalOcean VPS hosts. Missing workflow-relevant Codex skills were installed. No secret values are recorded here.

## Toolchain snapshot

| Component | Result | Evidence |
|---|---|---|
| Git | PASS | 2.50.1 |
| GitHub CLI | PASS | 2.96.0; keychain auth valid |
| Node.js | PASS | 26.5.0 |
| npm / npx | PASS | 11.17.0 |
| Python | PASS | system 3.9.6; Homebrew 3.12.13 available |
| pip | PASS | pip 26.1.2 under Python 3.12 |
| uv | PASS | 0.11.25 |
| Docker | PASS | Docker Desktop daemon healthy |
| Docker Compose | PASS | v5.2.0 |
| PM2 | PASS | installed and reachable |
| Ruff | PASS | 0.16.0 |
| Bandit | PASS | 1.8.6 |
| pip-audit | PASS | 2.9.0 |
| ESLint | PASS | 10.8.0 |
| Prettier | PASS | 3.9.6 |
| TypeScript | PASS | 7.0.2 |
| Claude Code CLI | PASS | 2.1.220 |
| Codex CLI | PASS | 0.144.3 |

## Skills and connectors

Installed during the audit:

- `openai-docs`
- `pdf`
- `screenshot`
- `speech`
- `transcribe`

Configured connectors and skills were present for GitHub, browser/control, computer-use, node REPL, Render, Sites, documents, spreadsheets, presentations, and visualization. No additional install was required during the audit.

## GitHub and SSH

- GitHub CLI auth is valid.
- GitHub SSH was configured to use the existing `empire_github_sync` key for `github.com`.
- Private SSH key permissions are restricted to `600`.
- No token, password, or private key material was recorded in this note.

## DigitalOcean VPS

- `64.227.6.197` (`empire-cpu`): SSH reachable; production Booking health was verified separately.
- `165.227.164.26` (`dzayn-app-prod`): SSH reachable; container inventory was read-only checked.

## Obsidian

Primary audit vault/repository:

`/Users/rolandgasparyan/Documents/Codex/2026-07-13/referenced-chatgpt-conversation-this-is-untrusted/work/obsidian-brain`

The vault has `.obsidian/` and `Projects/`, is a clean Git checkout, and receives this report.

## Security corrections

- Removed a plaintext `AIMLAPI_API_KEY` from `~/.zshrc` during the broader environment setup.
- Added a local-disk uv cache path to avoid cloud-cache index-lock failures.
- No secrets were copied into this report.

## Prior audit note preserved

An older 2026-07-25 environment audit for `6-EMPIRES-OS` recorded that the local baseline was usable but the GitHub-VPS-Obsidian chain still had drift: the legacy vault path was missing, the VPS checkouts were not a safe deployment source of truth, and the public `/chat` voice surface still needed STT/TTS routing work. That note is preserved here only as historical context.

## Safety gates

No trading, deposit, approval, rollback, or production safety gate was disabled during this audit.
