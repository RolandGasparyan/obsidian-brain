# Brain Sync Status

## Three-Way Sync: Obsidian Brain ⇄ GitHub ⇄ VPS — ✅ ACTIVE

- **Vault (canonical, editing):** iCloud → `Obsidian_Second_Brain`
- **GitHub:** `RolandGasparyan/obsidian-brain` — https://github.com/RolandGasparyan/obsidian-brain
- **VPS:** `165.227.164.26` (dzayn-app-prod) → `/root/obsidian-brain`
- **Codex workspace:** `~/Documents/Codex/2026-07-13/syn/work/`
- **Home sync script:** `~/.brain-sync/sync_brain.sh`
- **Auto-sync daemon:** `com.codex.brain-sync` (launchd, every 15 min — git operations)
- **VPS auto-pull:** cron job (every 15 min — pulls from bare repo)
- **Obsidian-git plugin:** auto-save/push/pull every 15 min (pushes directly to GitHub)

## Architecture

```
  Obsidian Brain (iCloud)
    ↓ obsidian-git plugin (auto-commit + push to GitHub every 15 min)
    ↓
  GitHub (obsidian-brain repo)
    ↓ launchd daemon (pull to workspace + push to VPS every 15 min)
    ↓ VPS cron (pull from bare repo every 15 min)
    ↓
  VPS (165.227.164.26 / dzayn-app-prod)
    /root/obsidian-brain (working clone)
    /root/obsidian-brain.git (bare repo)
```

## What's Configured

| Component | Status |
|---|---|
| Global git config | ✅ user: Roland Gasparyan <roland.gasparyan@gmail.com> |
| SSH config | ✅ github.com + vps-trading (165.227.164.26) |
| GitHub repo | ✅ created: https://github.com/RolandGasparyan/obsidian-brain |
| GitHub auth | ✅ gh CLI authenticated (scopes: repo, gist, read:org) |
| Vault git remote | ✅ https://github.com/RolandGasparyan/obsidian-brain.git |
| Vault git credential helper | ✅ gh auth git-credential (HTTPS) |
| obsidian-git plugin | ✅ auto-save/push/pull every 15 min |
| github-sync plugin | ✅ remote URL set to HTTPS |
| Codex workspace git | ✅ origin (GitHub HTTPS) + vps (SSH) |
| Home workspace git | ✅ ~/.brain-sync/work/ (for launchd daemon) |
| Launchd daemon | ✅ com.codex.brain-sync (every 15 min, git push/pull) |
| VPS cron job | ✅ every 15 min, pulls from bare repo |
| VPS bare repo | ✅ /root/obsidian-brain.git |
| VPS working clone | ✅ /root/obsidian-brain |

## Commands

```bash
# From terminal (full access — rsync + git)
~/Documents/Codex/2026-07-13/syn/sync_brain.sh status    # check sync state
~/Documents/Codex/2026-07-13/syn/sync_brain.sh sync      # full three-way sync
~/Documents/Codex/2026-07-13/syn/sync_brain.sh verify    # verify SHA parity

# From launchd daemon (git operations only — rsync blocked by TCC)
~/.brain-sync/sync_brain.sh status    # check sync state
~/.brain-sync/sync_brain.sh auto      # auto-sync (git push/pull only)

# Manage launchd daemon
launchctl unload ~/Library/LaunchAgents/com.codex.brain-sync.plist   # stop
launchctl load ~/Library/LaunchAgents/com.codex.brain-sync.plist     # start
```

## Last Master Sync

- **Timestamp:** 2026-07-13
- **Commit:** 8d33484 (fix: github-sync plugin remote URL to HTTPS)
- **Vault files:** 1318
- **GitHub:** https://github.com/RolandGasparyan/obsidian-brain
- **VPS:** 165.227.164.26 /root/obsidian-brain
- **All three in sync:** ✅
