# Brain Sync Status

## Three-Way Sync: Obsidian Brain ⇄ GitHub ⇄ VPS

- **Vault (canonical):** iCloud → `Obsidian_Second_Brain`
- **GitHub:** `RolandGasparyan/obsidian-brain`
- **VPS:** `vps-trading:/root/obsidian-brain`
- **Sync script:** `~/Documents/Codex/2026-07-13/syn/sync_brain.sh`
- **Auto-sync daemon:** `com.codex.brain-sync` (launchd, every 15 min)

## Configuration

| Setting | Value |
|---|---|
| Vault path | `~/Library/Mobile Documents/com~apple~CloudDocs/Obsidian_Second_Brain` |
| Git remote | `git@github.com:RolandGasparyan/obsidian-brain.git` |
| Branch | `main` |
| Auto-save interval | 15 min (obsidian-git) |
| Auto-push interval | 15 min (obsidian-git) |
| Auto-pull interval | 15 min (obsidian-git) |
| Auto-pull on boot | enabled |
| Pre-commit hook | SHA256 lock guard + secret scan |
| Launchd daemon | `com.codex.brain-sync` (every 15 min) |

## Commands

```bash
# Check sync state across all three
~/Documents/Codex/2026-07-13/syn/sync_brain.sh status

# Full three-way sync (pull + commit + push + VPS)
~/Documents/Codex/2026-07-13/syn/sync_brain.sh sync "my commit message"

# Just push to GitHub
~/Documents/Codex/2026-07-13/syn/sync_brain.sh push "my message"

# Just pull from GitHub
~/Documents/Codex/2026-07-13/syn/sync_brain.sh pull

# Verify SHA parity
~/Documents/Codex/2026-07-13/syn/sync_brain.sh verify

# One-time setup (if needed)
~/Documents/Codex/2026-07-13/syn/setup_sync.sh
```

## Last Master Sync
- **Timestamp:** 2026-07-13
- **Vault notes:** 362+
- **Repo:** obsidian-brain (new)
- **GitHub user:** RolandGasparyan
- **Sync method:** env-var override (sandbox-safe, no .git/config modification)

## Notes
- The vault's `.git/config` remote URL is set via environment variables at sync time
  (the sandbox prevents direct `.git/config` modification in iCloud)
- The obsidian-git plugin handles in-app auto-sync every 15 minutes
- The launchd daemon (`com.codex.brain-sync`) handles background sync
- The VPS pulls from GitHub automatically via the sync script

## SSH Key
- Key: `~/.ssh/id_ed25519_dzayn` (ed25519, "claude-code-dzayn-verify")
- Public key: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINlTptpoVGD2paoiQBaB/UJAZNhYvYPZHhmOhg+czqej`
- Config: `~/.ssh/config` (github.com + vps-trading + vps-legacy + vps-digital)
- **Must be registered on GitHub and VPS** — run `setup_sync.sh` to automate
