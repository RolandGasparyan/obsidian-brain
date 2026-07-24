# Booking AI Agent - Quick Reference Guide

**For:** Rapid development, debugging, deployment  
**Updated:** 2026-07-24  
**Status:** Production Stable

---

## ⚡ Critical CSS Fixes (Remember These!)

### Problem 1: Elements Force Overflow
**Symptom:** Button gets pushed off-screen on narrow viewports  
**Fix:** Add `min-width: 0` to parent flex/grid container
```css
#chatInput {
  display: grid;
  min-width: 0; /* THIS IS KEY */
}
```

### Problem 2: Grid Children Don't Shrink
**Symptom:** Text overflows in grid layout  
**Fix:** Add `min-width: 0` to parent + children
```css
#quickCmds {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
}
#quickCmds > button {
  min-width: 0;
  word-break: break-word;
}
```

### Problem 3: Long Content Overflows Viewport
**Symptom:** Toast notifications go off-screen  
**Fix:** Constrain width + enable wrapping
```css
.toast {
  max-width: calc(100vw - 32px);
  white-space: normal;
  word-break: break-word;
}
```

---

## 📱 Responsive Breakpoints

```css
/* Base styles (mobile 320px) */
#chatInput { /* icon-only mode */ }

/* Medium phones 480px+ */
@media (min-width: 480px) {
  #sendBtn { padding: 10px 12px; }
}

/* Tablets 768px+ */
@media (min-width: 768px) {
  #chatInput { flex-direction: row; }
  #brandSubtitle { display: block; }
}

/* Desktop 1280px+ */
@media (min-width: 1280px) {
  #chatContainer { max-width: 1200px; }
}
```

---

## 🌍 Multi-Language System

### Adding New Translations

**Step 1:** Add to `translations.js`
```javascript
const translations = {
  hy: {
    'myNewKey': 'Հայերեն տեքստ',
  },
  en: {
    'myNewKey': 'English text',
  },
  ru: {
    'myNewKey': 'Русский текст',
  }
};
```

**Step 2:** Use in HTML
```html
<!-- Text translation -->
<button data-i18n="myNewKey">English text</button>

<!-- Title/attribute translation -->
<div data-i18n-title="myNewKey" title="English text">Icon</div>
```

**Step 3:** JavaScript applies automatically
- `applyTranslations()` called on language change
- All `[data-i18n]` attributes updated
- All `[data-i18n-title]` attributes updated

### Supported Languages
- `hy` - Armenian (Հայերեն)
- `en` - English
- `ru` - Russian (Русский)

---

## 🎙️ Voice Commands Quick Setup

### Enable Voice for New Element
```javascript
// In app.js
document.getElementById('myButton').addEventListener('click', () => {
  startVoiceInput(); // Listen for speech
});

// Respond with voice
speakResponse("Your text here");
```

### Set Language for Voice Recognition
```javascript
function startVoiceInput() {
  const recognition = new webkitSpeechRecognition();
  
  // Language codes
  if (currentLanguage === 'hy') recognition.lang = 'hy-AM';
  if (currentLanguage === 'en') recognition.lang = 'en-US';
  if (currentLanguage === 'ru') recognition.lang = 'ru-RU';
  
  recognition.start();
}
```

---

## 📋 Common Tasks

### Testing Mobile Layout
```bash
# Run Playwright viewport tests
python shot.py  # Generates screenshots at 5 viewports

# Check for horizontal overflow
# Look for "overflow_px = 0" in output
```

### Check Deployment Status
```bash
# View latest workflow run
gh run list --limit 1

# Check production health
curl http://172.17.0.1:5000/health

# View current deployed commit
git log main -1 --oneline
```

### Deploy Changes
```bash
# Push to main (auto-deploys via GitHub Actions)
git push -u origin main

# Workflow runs automatically:
# 1. Security checks (20s)
# 2. Production deploy (31s)
# 3. Health check passes = live
```

### Run E2E Tests Locally
```bash
# Before making changes
npm test

# After changes
npm test
# Should show: 99/99 PASSED
```

---

## 🔧 Debugging Checklist

### Issue: Text Overflows on Mobile
- [ ] Parent has `display: grid` or `display: flex`?
- [ ] Parent has `min-width: 0`?
- [ ] Child element wrappable? `word-break: break-word`?
- [ ] Content uses `white-space: normal`?

### Issue: Send Button Cut Off
- [ ] Check `#chatInput` CSS
- [ ] Verify `min-width: 0` on parent
- [ ] Check button padding values
- [ ] Test at 320px, 375px, 414px viewports

### Issue: Calendar Shows Wrong
- [ ] Open panel at 100vh height?
- [ ] Close button clickable? Event listener wired?
- [ ] Grid centered with `justify-content: center`?
- [ ] Z-index high enough? (1000+)

### Issue: Language Not Switching
- [ ] Key exists in all 3 languages in `translations.js`?
- [ ] Element has `data-i18n="keyName"` attribute?
- [ ] `applyTranslations()` called after language change?
- [ ] Check browser console for errors

### Issue: Voice Not Working
- [ ] Browser supports Web Speech API? (Chrome/Edge/Safari)
- [ ] User granted microphone permission?
- [ ] Language code correct? (`hy-AM`, `en-US`, `ru-RU`)
- [ ] Event listener attached? `startVoiceInput()`

---

## 📊 Test Coverage Matrix

| Feature | Testing Method | Status |
|---------|-----------------|--------|
| Mobile Layout | Playwright 5 viewports | ✅ 99/99 E2E |
| Responsiveness | Media query CSS | ✅ Verified |
| Voice Commands | Browser manual test | ✅ Working |
| Languages | i18n switching | ✅ All 3 tested |
| Overflow | Visual inspection | ✅ Zero pixels |
| Deployment | Health check | ✅ Auto-verified |

---

## 🚀 Deployment Checklist

Before pushing to main:
- [ ] All changes committed locally
- [ ] Tests passing (`npm test`)
- [ ] No console errors
- [ ] Responsive design verified (3+ viewports)
- [ ] i18n strings added (all 3 languages)
- [ ] No hardcoded text (use `data-i18n`)

After push:
- [ ] GitHub Actions workflow starts
- [ ] Security checks pass (~20s)
- [ ] E2E tests pass (99/99)
- [ ] Production deploy starts (~31s)
- [ ] Health check passes ✅
- [ ] Live at 172.17.0.1:5000 in ~2 minutes

---

## 🔐 Security Reminders

- ✅ Never commit `.env` or API keys
- ✅ Sanitize user input (backend handles)
- ✅ Use `textContent` not `innerHTML` (XSS prevention)
- ✅ Validate dates/numbers before use
- ✅ HTTPS only in production
- ✅ Check CORS headers in deployment

---

## 📁 Key File Locations

| What | Where |
|------|-------|
| UI Layout | `static/index.html` |
| Business Logic | `static/app.js` |
| Translations | `static/translations.js` |
| Styles | `static/index.html` (inline) |
| CI/CD | `.github/workflows/ci-cd.yml` |
| Tests | `tests/e2e/` |
| Production Server | 172.17.0.1:5000 |

---

## ⏱️ Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Page Load | <2s | ✅ Met |
| Chat Response | <1s | ✅ Met |
| Voice Latency | <3s | ✅ Met |
| Mobile Render | <500ms | ✅ Met |

---

## 🆘 Emergency Procedures

### Production Is Down
```bash
# 1. Check health
curl http://172.17.0.1:5000/health

# 2. View recent commits
git log main -3

# 3. Rollback (if needed)
# Deployment auto-rollbacks on health check failure
# Manual rollback via VPS:
ssh vps "ln -sf /opt/booking/releases/previous/ /opt/booking/current"
```

### Tests Failing Locally
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Run tests again
npm test
```

### Can't Push to GitHub
```bash
# Check network
ping api.github.com

# Verify branch
git branch -vv

# Push again
git push -u origin main
```

---

## 💡 Pro Tips

1. **Always test at 3 viewports:** 375px (phone), 768px (tablet), 1280px (desktop)
2. **Use `min-width: 0`** on flex/grid parents when children should shrink
3. **Never hardcode text** - use `data-i18n` attributes instead
4. **Commit often** - small commits are easier to revert if needed
5. **Read error messages** - they tell you exactly what's wrong
6. **Voice needs HTTPS** - Web Speech API requires secure context
7. **Deploy = Push to main** - GitHub Actions handles everything else

---

## 📞 Support Commands

```bash
# See git log with author
git log --oneline --author="roland"

# List all branches
git branch -a

# Check uncommitted changes
git status

# View specific commit
git show 2f5586a

# Revert last commit (if needed)
git revert HEAD
```

---

*Keep this file open when working!*  
*Last verified: 2026-07-24 05:53:24 UTC*
