# PROJECT: REINCARNATION MUSIC EMPIRE — UNIFIED SPEC FOR DEV TEAM
# Author: Roland Gasparyan (Artist/Director/Producer) via Hermes Architect
# Date: 2026-10-10
# Status: FIRST DRAFT — for dev team alignment
# Rule: This doc is the single source of truth. Devs build ONLY from this + linked refs.
# Any change goes through Roland/Hermes first. Versioned and timestamped.

---

## 0. WHO WE ARE

Roland Gasparyan — Armenian composer, singer, music producer, spiritual philosopher.
Founder: Reincarnation Orchestra, Reincarnation Studios (label/management), HighYogi (fashion/art/spiritual), 6-empires (AI models corp), Vortex (media pipeline), Trading Guru AI Championship, Dzayn.app (wellness).

Brands share a unified spiritual/creative identity under "6-empires" AI infrastructure.

---

## 1. TOP-LEVEL ARCHITECTURE

6-empires is the parent AI corp. Under it, each brand is a semi-autonomous module sharing one backend.

```
6-empires (AI corp)
├── Reincarnation Orchestra (music/performance)
│   ├── reincarnation.am (artist site)
│   └── reincarnation-smm (social automation)
├── Reincarnation Studios (label, artist management)
│   ├── reincarnationstudios.com
│   └── booking-ai-agent (AI booking assistant)
├── HighYogi (creative brand)
│   └── highyogi.store (fashion/jewelry/art)
├── Trading Guru (AI competition)
│   ├── trading-guru-empire (metaworld)
│   └── strategy-lab-mac (paper trading lab)
├── Vortex (media production)
│   └── vortex (Hollywood-grade music+video pipeline)
├── Dzayn.app (wellness platform)
└── hermes-brain (meta-orchestrator)
```

**Shared platform**: AI/ML models, data lake, auth, payments, social APIs, notification layer.

**Isolation rule**: each brand has its own repo. Cross-brand features go through a shared API gateway only.

---

## 2. NEXT 90 DAYS — PRIORITY ROADMAP

### Phase 1 (Weeks 1-2): UNIFIED BACKBONE
**Goal**: one shared backend serving all brands. Eliminate per-brand silos.

**Deliverables**:
- `6-empires-api/` — main API (auth, profiles, payments, notifications, analytics)
- `6-empires-db/` — schema and migrations (PostgreSQL)
- `6-empires-auth/` — OAuth2 + social logins (Google, Apple, Spotify)
- `6-empires-ai/` — shared AI/ML layer (recommendations, content generation, artist matching)

**Roland provides**: brand identity docs, artist roster, music/audio files, merch catalog, show concepts for the first 3 months.

### Phase 2 (Weeks 3-5): REINCARNATION ORCHESTRA
**Goal**: the artist platform, ready to launch.

**Deliverables**:
- `reincarnation.am/` — artist site (Next.js)
  - Hero: Reincarnation Orchestra identity + "When Music Heals the Soul"
  - Music: player, albums, lyrics (with translations: ENG/ARM/RUS)
  - Tour: upcoming shows, ticket links (Eventbrite/official)
  - Merch: HighYogi store integration
  - About: story, philosophy, gallery
  - Contact: booking, press, collaboration
- `booking-ai-agent/` — AI booking assistant (from BOOKING-AI-AGENT repo)
  - Input: event details (dates, venue type, budget)
  - Output: generated agreement, artist rider, logistics checklist
  - Integration: Google Calendar for Roland + team
- `reincarnation-smm/` — social media automation (already exists)
  - Upgrade: unified across all brands, auto-posting from content calendar
  - Platforms: Instagram, TikTok, YouTube, X, Facebook, Telegram

### Phase 3 (Weeks 6-8): HIGHYOGI STORE
**Goal**: merge HighYogi into the main platform. Fashion + art + spiritual.

**Deliverables**:
- `highyogi.store/` — Shopify or custom Next.js
  - Three verticals: Fashion, Jewelry, Art Paintings
  - Spiritual commerce angle: each piece is a "portal" or "gateway"
  - Integration: shared auth, shared payments, artist royalties
- `highyogi-content/` — AI-assisted product storytelling
  - Each item has a "meditation card" describing its spiritual meaning
  - Roland writes the concept, AI generates variants for A/B testing

### Phase 4 (Weeks 9-12): 6-EMPIRES AI LAYER + TRADING GURU
**Goal**: public launch of 6-empires as the AI corp. Trading Guru as the demo.

**Deliverables**:
- `6-empires.com/` — corporate AI site
  - Showcase: AI models in music (composition, mastering), trading (championship), art generation
  - Developer portal: API docs, playground, model demos
  - News: AI research papers, releases, model updates
- `trading-guru-empire/` — AI trading championship (already exists)
  - 8 AI agents, live leaderboards, multi-language (ENG/ARM/RUS)
  - Integration: shared auth for cross-brand community
  - Monetization: entry fees, premium analytics, sponsored tournaments

---

## 3. SHARED DATA MODELS

```json
// Artist (Reincarnation Studios)
{
  "artist_id": "uuid",
  "name": "string",
  "bio": "text (multi-lang)",
  "genres": ["string"],
  "spiritual_themes": ["string"],
  "social_links": {},
  "discography": ["album_id"],
  "booking_status": "available | booked | tour",
  "management": { "label": "Reincarnation Studios", "agent": "Roland" }
}

// Release (album/single/video)
{
  "release_id": "uuid",
  "artist_id": "uuid",
  "type": "album | single | video | live",
  "title": "string",
  "release_date": "date",
  "streaming_links": { "spotify": "", "apple": "", "youtube": "" },
  "lyrics": { "original": "", "translations": {} },
  "credits": [{ "role": "producer|writer|...", "name": "" }]
}

// Trading Profile (Trading Guru)
{
  "trader_id": "uuid",
  "ai_model": "string (e.g., GPT-4-Trader, Claude-Quant)",
  "strategy": "string",
  "leaderboard_rank": "int",
  "pnl_history": [{}],
  "championship_entries": ["champ_id"]
}

// Product (HighYogi)
{
  "product_id": "uuid",
  "collection": "fashion | jewelry | art",
  "name": "string",
  "spiritual_meaning": "text",
  "limited_edition": "bool",
  "artist_royalty_pct": "float"
}
```

---

## 4. APIS (SHARED GATEWAY)

Base: `api.6-empires.com/v1`

```
# Auth
POST   /auth/login?provider=google|apple|spotify
GET    /auth/me
POST   /auth/logout

# Artists
GET    /artists?genre
POST   /artists         (label only)
GET    /artists/:id

# Releases
GET    /releases?artist_id
POST   /releases        (label only)

# Booking
POST   /booking/request
GET    /booking/availability

# Trading Guru
GET    /trading/leaderboard
GET    /trading/agents
POST   /trading/championship/enter

# Commerce (HighYogi)
GET    /shop/products?collection
POST   /shop/orders
GET    /shop/products/:id/meditation-card

# AI (6-empires)
POST   /ai/compose-music
POST   /ai/trading-strategy
POST   /ai/generate-art
```

**Rule**: all brand sites consume ONLY these APIs. No direct DB access from frontend.

---

## 5. CREATIVE DIRECTION (ROLAND'S VISION)

### Brand Tone
- **Reincarnation Orchestra**: spiritual, powerful, cosmic, healing. "Ancient future."
- **Reincarnation Studios**: cutting-edge, nurturing, high-standard, global.
- **HighYogi**: exclusive, meditative, wearable art, spiritually charged.
- **Trading Guru**: competitive, gamified, transparent, elite.
- **6-empires**: futuristic, trustworthy, AI-native, human-creative hybrid.

### Visual Language
- Colors: deep black, gold, amber, deep violet (spiritual palette)
- Typography: modern serif (for elegance) + clean sans (for utility)
- Motion: slow, cinematic, purposeful. Never flashy, always meaningful.

### Non-Negotiables
- Armenian identity visible in every brand, not as decoration but as foundation.
- English as primary language, Armenian and Russian as first-class locals.
- Every product/song/show has a spiritual layer (meaning > marketing).

---

## 6. WHAT ROLAND PROVIDES THIS WEEK

- [ ] Brand guidelines (colors, fonts, logos) for all 4 active brands
- [ ] Artist roster (Reincarnation Orchestra + signed/unsigned talent)
- [ ] First 10 HighYogi product concepts (name, image, spiritual meaning)
- [ ] Tour dates + venues list (next 6 months)
- [ ] Reference artists/creators each brand should feel like
- [ ] $10M video production brief (what equipment, what style, what team)
- [ ] AI model preferences for trading agents (which models to allow in Trading Guru)

## 7. WHAT DEV TEAM DELIVERS THIS WEEK

- [ ] Repo structure: monorepo vs per-repo decision (advise, then standardize)
- [ ] Local dev environment (Docker compose for all services)
- [ ] CI/CD pipeline: GitHub Actions → staging → production
- [ ] Shared design system component library (Figma → Storybook)
- [ ] Database schema v0.1 (from models above)
- [ ] API gateway skeleton (FastAPI or tRPC, typed, versioned)
- [ ] Auth flow: social login working on staging

---

## 8. ACCEPTANCE CRITERIA (PHASE 1)

A dev team member can:
1. Log in with Google/Apple/Spotify on any brand site and have the same session on all others.
2. View Reincarnation Orchestra's artist profile, play a track, see lyrics in 3 languages.
3. Submit a booking request form that generates a draft agreement.
4. Browse HighYogi products by collection, add to cart, check out with shared payment.
5. See Trading Guru leaderboard with 8 AI agents ranked live.

---

## 9. RISKS & RULES

- **Scope creep**: this doc covers 90 days. New features go to backlog, not into active sprints.
- **Brand silos**: no separate backends per brand. All data flows through the shared gateway.
- **AI dependence**: AI assists creativity; it never replaces Roland's final creative decision.
- **Data privacy**: fan data and artist data must be encrypted at rest and in transit.

---

## 10. NEXT REVIEW

- Next sync: Monday, October 13, 2026
- Owner: Roland (vision) ↔ Hermes (architecture) ↔ Dev Lead (execution)
- Update this doc after every review with timestamp and version number.

Version: 1.0 | Last updated: 2026-10-10 | By: Hermes Chief Architect
