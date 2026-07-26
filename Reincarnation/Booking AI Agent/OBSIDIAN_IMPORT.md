# Reincarnation Booking AI Agent - Obsidian Vault Guide

**Purpose:** Complete documentation structure for Obsidian Brain  
**Format:** Markdown (ready to import)  
**Updated:** 2026-07-24

---

## 📚 Recommended Vault Structure

```
Reincarnation/
├── 🚀 Projects/
│   └── Booking AI Agent/
│       ├── 📋 Overview.md
│       ├── 🏗️ Architecture.md
│       ├── 📝 Deployment Log.md
│       ├── ⚡ Quick Reference.md
│       ├── 🔧 Development/
│       │   ├── Mobile Layout Fixes.md
│       │   ├── Voice Commands.md
│       │   └── i18n System.md
│       ├── 🧪 Testing/
│       │   ├── E2E Tests.md
│       │   └── Viewport Testing.md
│       └── 🚨 Emergency Procedures.md
├── 📖 References/
│   ├── GitHub Links.md
│   ├── VPS Configuration.md
│   └── API Endpoints.md
└── 📅 Changelog.md
```

---

## 🔗 Quick Links for Obsidian

### Main Project Files
- **GitHub Repository:** https://github.com/rolandgasparyan/booking-ai-agent
- **Production URL:** https://6-empires.com
- **VPS Gateway:** 172.17.0.1:5000
- **Development Branch:** claude/booking-ai-agent-sync-ksu0yk

### Key Documentation
- [[DEPLOYMENT_LOG.md|Deployment History]]
- [[ARCHITECTURE.md|System Architecture]]
- [[QUICK_REFERENCE.md|Developer Quick Reference]]

### Technologies
- **Frontend:** HTML5, CSS3 (Flexbox/Grid), JavaScript (Web Speech API)
- **Backend:** Python (FastAPI/Flask)
- **VPS:** Docker, Atomic Deployment
- **CI/CD:** GitHub Actions
- **Languages:** Armenian, English, Russian

---

## 📌 Obsidian Tags (Recommended)

```markdown
#booking-ai-agent
#reincarnation
#production
#mobile-responsive
#voice-commands
#multi-language
#deployment
#vps
#github-actions
#css-flexbox
#responsive-design
#e2e-testing
```

### Usage Example
```markdown
# Fix Mobile Layout Overflow
#booking-ai-agent #mobile-responsive #css-flexbox

Problem: Send button cut off on 320px viewport
Solution: Added `min-width: 0` to flex parent
Status: ✅ Deployed, verified
```

---

## 📊 Obsidian Dataview Queries (Optional)

### Active Issues
```dataview
TABLE status, priority
FROM "Booking AI Agent"
WHERE type = "issue" AND status != "resolved"
```

### Completed Fixes
```dataview
LIST file.link
FROM "Booking AI Agent"
WHERE type = "fix" AND status = "deployed"
```

### Urgent Items
```dataview
TABLE updated
FROM "Booking AI Agent"
WHERE priority = "urgent"
SORT updated DESC
```

---

## 🎯 Import Steps

### Method 1: Copy-Paste Files
1. Create folder: `Booking AI Agent` in Obsidian vault
2. Copy content from GitHub:
   - DEPLOYMENT_LOG.md
   - ARCHITECTURE.md
   - QUICK_REFERENCE.md
3. Create subfolders: Development/, Testing/, References/
4. Add individual topic notes

### Method 2: Direct Import from GitHub
1. Obsidian Vault Settings → Sync
2. Add GitHub as remote source
3. Pull files automatically
4. Organize in Local Vault

### Method 3: Clone Repository
```bash
# In your Obsidian vault root
git clone https://github.com/rolandgasparyan/booking-ai-agent.git

# Then in Obsidian, create symlink or copy structure
```

---

## 🗒️ Note Template - Development Tasks

```markdown
---
type: task
status: in_progress
priority: high
tags: [#booking-ai-agent, #mobile-responsive]
due: 2026-07-31
---

# [Task Name]

## Description
What needs to be done?

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Related Files
- [[DEPLOYMENT_LOG.md]]
- [[ARCHITECTURE.md]]

## Implementation Notes
- Flexbox/Grid considerations
- Responsive breakpoints (320px, 480px, 768px, 1280px)
- i18n requirements

## Status Timeline
- Started: YYYY-MM-DD
- In Progress: YYYY-MM-DD
- Testing: YYYY-MM-DD
- Deployed: YYYY-MM-DD

## Testing Results
- [ ] Mobile (375px)
- [ ] Tablet (768px)
- [ ] Desktop (1280px)
- [ ] E2E tests passing
- [ ] Voice features working

## References
- GitHub PR: https://github.com/rolandgasparyan/booking-ai-agent/pull/XX
- Workflow: https://github.com/rolandgasparyan/booking-ai-agent/actions
```

---

## 🗒️ Note Template - Deployment Records

```markdown
---
type: deployment
date: 2026-07-24
version: 2.0
status: live
tags: [#deployment, #production, #verified]
---

# Deployment v2.0 - Mobile Layout Optimization

## Commit
- SHA: 2f5586a
- Branch: main
- PR: #94

## Changes Deployed
1. Mobile layout overflow fixes
2. Calendar close button added
3. Toast notification wrapping
4. Responsive media queries

## Verification
- ✅ Security checks passed
- ✅ E2E tests: 99/99 passed
- ✅ Health check: Passed
- ✅ Production: Live at 172.17.0.1:5000

## Performance
- Deployment time: 31 seconds
- Security scan: 20 seconds
- No issues detected

## Links
- [[DEPLOYMENT_LOG.md]]
- GitHub: https://github.com/rolandgasparyan/booking-ai-agent
```

---

## 🗒️ Note Template - Bug Fix/Feature

```markdown
---
type: issue
status: resolved
component: mobile-layout
severity: high
tags: [#bug-fix, #mobile-responsive, #css]
date_created: 2026-07-23
date_resolved: 2026-07-24
---

# Send Button Cut Off on Mobile Viewports

## Problem Statement
Send button appears off-screen on viewports 320px-375px wide.

## Root Cause
CSS Grid child element (`#chatInput`) had default `min-width: auto`, 
preventing flex items from shrinking below content size.

## Solution
```css
#chatInput {
  display: grid;
  min-width: 0;  /* KEY FIX */
  grid-template-columns: 1fr auto;
  gap: 8px;
}
```

## Files Modified
- static/index.html (CSS changes)
- static/app.js (event listeners)

## Testing
- Playwright: 5 viewports (320px-1280px)
- E2E: 99/99 passing
- Manual: Verified on iPhone, Android

## Deployed
- Date: 2026-07-24
- Workflow: #160
- Status: ✅ Live

## References
- [[ARCHITECTURE.md|Responsive Design Strategy]]
- [[QUICK_REFERENCE.md|CSS Fixes]]
```

---

## 📅 Suggested Obsidian Plugins

**Recommended for this project:**

| Plugin | Purpose |
|--------|---------|
| Dataview | Create queries for tasks/issues |
| Templater | Auto-fill note templates |
| Git | Sync with GitHub automatically |
| Calendar | Track deployment dates |
| Backlinks | Link related documentation |
| Tags | Organize by category |
| Excalidraw | Diagram architecture |
| Advanced Tables | Format data clearly |

---

## 🔄 Sync Workflow

### Automatic Sync (if Git plugin enabled)
```bash
# Obsidian syncs with GitHub automatically
# Changes push/pull on file save
```

### Manual Sync
```bash
# From Obsidian terminal or external:
git pull origin main
git push origin main
```

### Steps:
1. ✅ Make changes in Obsidian
2. ✅ Save file (auto-sync if enabled)
3. ✅ Push to GitHub
4. ✅ Verify on https://github.com/rolandgasparyan/booking-ai-agent

---

## 💾 Backup Strategy

**Recommended:**
- ✅ GitHub (version control)
- ✅ Obsidian Vault (local copy)
- ✅ VPS Server (production reference)
- ✅ Cloud sync (Obsidian Sync subscription)

---

## 📋 Initial Checklist for Obsidian Setup

- [ ] Create vault: "Reincarnation"
- [ ] Create folder: "Booking AI Agent"
- [ ] Copy main documents:
  - [ ] DEPLOYMENT_LOG.md
  - [ ] ARCHITECTURE.md
  - [ ] QUICK_REFERENCE.md
- [ ] Create subfolder: Development/
- [ ] Create subfolder: Testing/
- [ ] Create subfolder: References/
- [ ] Install recommended plugins
- [ ] Set up Git sync (optional)
- [ ] Create daily note template
- [ ] Add tags to existing notes
- [ ] Test backlinks
- [ ] Verify sync to GitHub

---

## 🚀 Obsidian Daily Workflow

**Morning Check:**
1. Open "Booking AI Agent" project
2. Review [[DEPLOYMENT_LOG.md|recent deployments]]
3. Check for ⚠️ urgent issues
4. Plan day's work

**During Development:**
1. Create task note (use template)
2. Link to related documentation
3. Update status as you progress
4. Save (auto-syncs)

**End of Day:**
1. Update task status
2. Document findings
3. Create deployment note if pushed
4. Commit to GitHub

---

## 🎯 Example Dashboard Note

```markdown
# Booking AI Agent - Dashboard

## Status: ✅ Production Live

**Latest Deployment:** 2026-07-24  
**E2E Tests:** 99/99 ✅ Passing  
**Health Check:** ✅ Passing  

## Quick Stats
- Responsive viewports: 5 (320px-1280px)
- Languages supported: 3 (hy, en, ru)
- Voice commands: Enabled
- Deployment time: 31 seconds

## Recent Fixes
- [[Mobile Layout Overflow]]
- [[Calendar Close Button]]
- [[Toast Notification Wrapping]]

## Next Tasks
- [ ] Monitor production metrics
- [ ] Gather user feedback
- [ ] Plan v2.1 features

## Links
- GitHub: https://github.com/rolandgasparyan/booking-ai-agent
- Live: https://6-empires.com
- VPS: 172.17.0.1:5000
- [[QUICK_REFERENCE.md|Developer Reference]]
```

---

## 📞 Contact & Links

- **Owner:** Roland Gasparyan
- **Email:** roland.gasparyan@gmail.com
- **GitHub:** rolandgasparyan
- **Repository:** https://github.com/rolandgasparyan/booking-ai-agent

---

*This document is formatted for Obsidian import*  
*Last updated: 2026-07-24*  
*Status: Ready for vault integration*
