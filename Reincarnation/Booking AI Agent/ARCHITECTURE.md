# Reincarnation Booking AI Agent - Architecture

**Version:** 2.0 (Mobile Optimized)  
**Status:** Production  
**Last Updated:** 2026-07-24

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Browser (Client)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              index.html (Responsive UI)              │   │
│  │  - Flexbox/Grid layout with min-width:0 fixes       │   │
│  │  - Media queries: 768px, 480px, 380px               │   │
│  │  - Chat input, quick commands, calendar panel       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  app.js (Business Logic & Event Handlers)            │   │
│  │  - Message handling                                  │   │
│  │  - Voice commands (Web Speech API)                   │   │
│  │  - Calendar management                               │   │
│  │  - Language switching                                │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  translations.js (i18n Strings)                      │   │
│  │  - Armenian (hy), English (en), Russian (ru)         │   │
│  │  - Language keys + translations                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    Backend Server (Python)                   │
│  - FastAPI / Flask (booking endpoints)                       │
│  - AI model inference (text/voice processing)                │
│  - Calendar management                                       │
│  - Database (bookings, users)                                │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    Production Server (VPS)                   │
│  Gateway: 172.17.0.1:5000                                    │
│  - Atomic deployment (symlink switching)                     │
│  - Health checks                                             │
│  - Auto-rollback on failure                                  │
│  - HTTPS/SSL termination                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 Frontend Architecture

### Component Breakdown

#### 1. **Chat Interface**
```html
<div id="chatContainer">
  <div id="chatBox"></div>
  <div id="chatInput">
    <input id="userInput" />
    <button id="sendBtn">Send</button>
  </div>
</div>
```

**Responsive Behavior:**
- 768px+: Full width, normal padding
- 480px: Reduced padding (10px 9px on buttons)
- 380px: Icon-only send button, hide label text

**Key CSS Fix:**
```css
#chatInput {
  display: grid;
  grid-template-columns: 1fr auto;
  min-width: 0; /* Critical: allows shrinking */
  gap: 8px;
}
```

#### 2. **Quick Commands Panel**
```html
<div id="quickCmds">
  <button>Book Appointment</button>
  <button>Check Availability</button>
  <button>Voice Commands</button>
</div>
```

**Problem:** Long Armenian text (e.g., "Վերականգնել վերահանդիսավորում") overflows  
**Solution:**
```css
#quickCmds {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
}
#quickCmds > button {
  min-width: 0;
  word-break: break-word;
  overflow-wrap: break-word;
}
```

#### 3. **Calendar Panel**
```html
<div id="calendarPanel">
  <div id="calHeader">
    <span>Calendar</span>
    <button id="calClose">✕</button>
  </div>
  <div id="calGrid"></div>
</div>
```

**Issues Fixed:**
- ❌ No close button on mobile → ✅ Added `#calClose` button
- ❌ Empty space at bottom → ✅ Changed grid to flexbox with `justify-content: center`
- ❌ Full-screen overlay issues → ✅ Proper z-index and overlay handling

**Current CSS:**
```css
#calendarPanel {
  position: fixed;
  right: 0;
  top: 0;
  height: 100vh;
  width: 290px;
  background: white;
  box-shadow: -2px 0 8px rgba(0,0,0,0.1);
  overflow-y: auto;
  z-index: 1000;
}

#calGrid {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 100vh;
}
```

#### 4. **Toast Notifications**
**Problem:** Long messages overflow viewport  
**Solution:**
```css
.toast {
  max-width: calc(100vw - 32px);
  width: max-content;
  white-space: normal;
  word-break: break-word;
  text-align: center;
}
```

### Responsive Design Strategy

**Philosophy:** Mobile-first with progressive enhancement

| Viewport | Strategy |
|----------|----------|
| 320px | Hide non-essential UI, icon-only buttons, stack everything |
| 375px | Reduce padding, keep labels, optimize spacing |
| 768px | Tablet layout, sidebar space |
| 1280px | Desktop, full features |

**Media Query Cascade:**
```css
/* Default (mobile) */
#sendBtn { padding: 10px 12px; }

/* 480px and up */
@media (min-width: 480px) {
  #sendBtn { padding: 10px 12px; }
}

/* 768px and up */
@media (min-width: 768px) {
  #sendBtn { padding: 12px 16px; }
}
```

---

## 🗣️ Voice & Language System

### Multi-Language Support (i18n)

**Language Keys:** `hy` (Armenian), `en` (English), `ru` (Russian)

**Translation System:**
```javascript
// translations.js
const translations = {
  hy: {
    'sendButton': 'ՈՒՂԱՐԿԵԼ',
    'calendarCloseTitle': 'Փակել օրացույցը',
    'bookingConfirm': 'Ձեր ամսագրում հաստատվել է',
  },
  en: {
    'sendButton': 'SEND',
    'calendarCloseTitle': 'Close calendar',
    'bookingConfirm': 'Your booking is confirmed',
  },
  ru: {
    'sendButton': 'ОТПРАВИТЬ',
    'calendarCloseTitle': 'Закрыть календарь',
    'bookingConfirm': 'Ваше бронирование подтверждено',
  }
};
```

**HTML Usage:**
```html
<button id="sendBtn" data-i18n="sendButton">SEND</button>
<div id="calendarPanel">
  <button id="calClose" data-i18n-title="calendarCloseTitle">✕</button>
</div>
```

**JavaScript Application:**
```javascript
function applyTranslations(lang = currentLanguage) {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = translations[lang][key];
  });
  
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    el.title = translations[lang][key];
  });
}
```

### Voice Commands (Web Speech API)

**Supported:**
- ✅ Chrome, Edge, Safari, Opera
- ✅ Armenian, English, Russian
- ✅ Continuous listening
- ✅ Real-time feedback

**Implementation:**
```javascript
function startVoiceInput() {
  const recognition = new webkitSpeechRecognition();
  recognition.lang = currentLanguage === 'hy' ? 'hy-AM' : 
                     currentLanguage === 'ru' ? 'ru-RU' : 'en-US';
  
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById('userInput').value = transcript;
  };
  
  recognition.start();
}

function speakResponse(text) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = currentLanguage === 'hy' ? 'hy' : 
                   currentLanguage === 'ru' ? 'ru' : 'en';
  window.speechSynthesis.speak(utterance);
}
```

---

## 🔄 Event Flow

### Message Sending Flow

```
User Input
    ↓
sendMessage() triggered
    ↓
Validate input
    ↓
Add to chat history
    ↓
Send to backend
    ↓
Backend processes (AI inference)
    ↓
Receive response
    ↓
Display in chat
    ↓
Apply translations
    ↓
Optional: Speak response
```

### Calendar Opening/Closing

```
User clicks calendar icon
    ↓
openCalendar() triggered
    ↓
calendarPanel.classList.add('open')
    ↓
Fetch events from backend
    ↓
Render calendar grid
    ↓
User clicks close button (✕)
    ↓
closeCalendar() triggered
    ↓
calendarPanel.classList.remove('open')
    ↓
Clear calendar grid
```

### Language Switching

```
User selects language (hy/en/ru)
    ↓
currentLanguage = 'en' (example)
    ↓
applyTranslations('en')
    ↓
Update all [data-i18n] elements
    ↓
Update voice recognition language
    ↓
Save preference to localStorage
```

---

## 🧪 Testing Architecture

### Test Suites

| Suite | Tests | Purpose |
|-------|-------|---------|
| E2E | 99 | Full user workflows |
| Integration | 15 | Backend API endpoints |
| Unit | 25 | Individual functions |

### Playwright Viewport Testing

**Tested Widths:**
- 320px (small phone)
- 375px (standard phone)
- 414px (large phone)
- 768px (tablet)
- 1280px (desktop)

**Checks:**
- ✅ Horizontal overflow = 0px
- ✅ Send button always visible
- ✅ Calendar panel renders correctly
- ✅ No text overflow on buttons
- ✅ Toast notifications within viewport

---

## 🚀 Deployment Pipeline

### GitHub Actions Workflow

**Trigger:** Push to main branch

**Jobs:**

1. **Security & Tests** (20s)
   - Code compile
   - Lint (ESLint, StyleLint)
   - Security scan (Bandit, pip-audit)
   - E2E tests (99/99)

2. **Atomic Deploy** (31s)
   - Upload release to VPS
   - Install dependencies
   - Atomic switch (symlink)
   - Health check (✅ PASSED)
   - Auto-rollback on failure

### Atomic Deployment Process

```
Current Live:
/opt/booking/current -> /opt/booking/releases/v2.1/

Deploy v2.2:
1. Create: /opt/booking/releases/v2.2/
2. Upload files
3. Install deps
4. Test: curl http://172.17.0.1:5000/health
5. Switch: ln -sf /opt/booking/releases/v2.2/ /opt/booking/current
6. If test fails: ln -sf /opt/booking/releases/v2.1/ /opt/booking/current (rollback)
```

---

## 📊 Performance Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Page Load | <2s | ✅ Good |
| Chat Response | <1s | ✅ Good |
| Voice Recognition | <3s | ✅ Good |
| Mobile Render | <500ms | ✅ Excellent |
| Zero Overflow | All viewports | ✅ Verified |

---

## 🔐 Security Measures

- ✅ HTTPS/SSL (VPS)
- ✅ XSS prevention (sanitized inputs)
- ✅ CSRF tokens (if needed)
- ✅ Input validation (backend)
- ✅ Rate limiting (backend)
- ✅ Security headers (CORS, CSP)

---

## 📝 Key Code Files Reference

| File | Purpose | Lines |
|------|---------|-------|
| `static/index.html` | UI layout & styles | 200+ |
| `static/app.js` | Core logic | 400+ |
| `static/translations.js` | i18n strings | 100+ |
| `.github/workflows/ci-cd.yml` | CI/CD pipeline | 80+ |

---

## 🎯 Feature Matrix

| Feature | Status | Notes |
|---------|--------|-------|
| Chat Interface | ✅ | Full responsive |
| Voice Commands | ✅ | 3 languages |
| Calendar Panel | ✅ | Mobile close button |
| Multi-Language | ✅ | hy/en/ru |
| Mobile Layout | ✅ | 320px-1280px verified |
| Booking System | ✅ | Backend integrated |
| Toast Notifications | ✅ | Viewport wrapping |
| Health Checks | ✅ | Auto-monitoring |

---

*Generated: 2026-07-24*  
*Can be imported to Obsidian as-is*
