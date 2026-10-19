# REINCARNATION ORCHESTRA — FULLY-DETAILED SPECIFICATION FOR DEV TEAM

Version: 1.0 | Date: 2026-10-10 | Owner: Roland Gasparyan (Artist/Director/Producer) | Architect: Hermes
Rule: This doc is the single source of truth. Devs build ONLY from this. Any change goes through Roland/Hermes and is versioned. No ad-hoc creative decisions in code.

---

## 1. VISION LAYER (Artist/Director)

**Brand essence**: Armenian musical heritage fused with modern cosmic/spiritual music. The Orchestra is not just a band; it is a movement for healing, unity, and transformation through sound. The tagline is "When Music Heals the Soul".

**Emotional tone**: powerful, spiritual, healing, high-energy live, deep introspection in recordings. The live experience drives global fandom; the recordings drive artistic depth and critical respect.

**Unique angle (no competitor has)**: every Reincarnation Orchestra release, show, and merch item is embedded with *intentional meaning* (spiritual/cultural). Fans don't just listen; they participate in meaning. This is the differentiator that sells tickets, merch, and sponsorship.

**Target audience**: spiritually-oriented global music fans, Armenian diaspora (ENG/ARM/RUS), premium live event attendees, culturally curious younger listeners, and spiritually-inclined music collectors.

**Primary artistic references** (for the dev team to understand what "feels right"): *HammerFall* power, *Kamelot* cinematic scope, *Ayreon* storytelling, and Armenian classical/spiritual motifs (Komitas-style harmonic depth) blended into modern production.

**Non-negotiables**:
* Armenian identity is visible in every asset, not as decoration but as foundation (language, themes, instruments).
* Every release has a spiritual narrative (what it means, not just how it sounds).
* Live show narrative: from opening invocation to final release, the show is a journey, not a concert.

---

## 2. BUSINESS LAYER (Producer/Manager)

**Revenue model**:
1. Live events (tickets, VIP, meet&greet, packages)
2. Streaming and sales (Spotify, Apple Music, YouTube, physical vinyl/special editions)
3. High-margin merch (HighYogi integration): limited-edition apparel, jewelry, art
4. Booking and label services (Reincarnation Studios): signing and managing talent under the same ethos
5. Content and licensing (documentary, soundtrack work, branded spiritual content)

**Pricing strategy**: premium, limited-availability drops, tour packages that bundle merch + content access. Every price point must tie to an emotional benefit, not just a commodity.

**Market size**: global symphonic/spiritual metal + world fusion + art-rock audience multiplied by Armenian cultural reach and modern wellness music trends. Early growth via diaspora and festival networks, then crossover into mainstream conscious music audiences.

**KPIs for the platform** (devs need measurable targets):
* 10,000+ monthly active unique visitors on the artist site by month 3 after launch
* 2,000+ live event ticket sales per major market tour stop
* 15%+ conversion from site visit to merch or ticket purchase
* 80%+ email capture for announcements (fan data sovereignty: we own our audience)

**Timeline**: Weeks 1-2 backend skeleton; Weeks 3-5 platform live; Weeks 6-8 booking automation and merch; Weeks 9-12 AI layer and analytics. Hard launch tied to first major tour announcement.

**Team requirements**: 2 backend engineers (API/auth/database), 2 frontend engineers (site/store), 1 integrations engineer (Spotify/Apple/YouTube/Eventbrite), 1 AI/ML engineer (recommendations, content generation), 1 QA engineer (tickets, payments, uptime), 1 designer (Roland-approved brand system), 1 product manager (keeps scope), and 1 community manager (fan engagement).

---

## 3. TECH LAYER (Dev Team)

**Recommended stack**:
* **Backend**: Python (FastAPI) for the shared gateway; TypeScript (Node.js) for event-driven SMM/integrations where realtime is needed
* **Frontend**: Next.js (React) for the artist site and store; static generation for tour pages to survive traffic spikes
* **Database**: PostgreSQL (shared primary) with Redis for session/queue; separate analytics DB (ClickHouse or DuckDB for scale-out queries)
* **Infrastructure**: Docker Compose for local; Kubernetes for staging/production; CDN for media (videos, stems, artwork); object storage (S3-compatible) for stems/merch art
* **Integrations**: Stripe (payments), Eventbrite or custom ticket provider (tickets), Spotify/Apple/YouTube APIs (music), Instagram/TikTok/YouTube APIs (social), Mailchimp or own CRM (owned audience)

**Repository layout (single source of truth)**:
```
/6-empires                    (monorepo decision: per-brand repos under an org folder, shared packages as git submodules)
  /packages
    /auth                     (OAuth2 flows, JWT sessions, provider adapters)
    /api-gateway              (versioned REST/tRPC endpoints with auth)
    /database                 (schema, migrations, shared types)
    /design-system            (tokens, components, theme, Roland's palette)
    /media                    (uploads, processing, CDN helpers)
  /apps
    /reincarnation-orchestra  (Next.js artist site)
    /reincarnation-studios    (Next.js label site)
    /highyogi-store           (Next.js commerce)
    /trading-guru             (competition frontend)
    /booking-ai-agent         (Node.js or Python service)
    /smm-automation           (Node.js social pipeline)
    /shared-backend           (FastAPI)
```

**Environment separation**:
* `dev` (local Docker, self-signed certs, mock external APIs)
* `staging` (full stack, sandbox payments, real third-party keys, mirrored from production DB nightly)
* `prod` (blue/green deploys, monitoring, alerting, encrypted secrets, rate limiting, WAF)

**Security constraints** (explicit and testable):
* All secrets in KMS/Vault, never in code or CI logs
* All user data encrypted at rest (AES-256-GCM) and in transit (TLS 1.3+)
* Auth tokens are short-lived, refresh tokens rotated, social logins use PKCE
* API rate limited per IP + per user, abuse triggers alerts to the team
* Merch and ticketing flows must pass fraud checks (velocity rules, payment scoring, 3DS)

**Integrations with explicit contracts**:
* Spotify: client credentials + user tokens for playback, releases, follow data; handle 429s with backoff
* Apple Music: developer token, catalog search, playback; handle expiring tokens
* YouTube: OAuth2 for channel and video stats; quota-aware batching
* Eventbrite: OAuth for events and orders; webhooks for sales updates
* Social platforms: per-brand tokens, scheduled publishing, engagement metrics pulled hourly not realtime to avoid rate-limit bans

**File structure (explicit, testable)**:
```
/apps/reincarnation-orchestra
  public/                     (static assets: logos, fonts, audio stems)
  src/
    pages/                    (routes: home, music, tour, merch, about, contact)
    components/               (player, tour-card, lyric-panel, product-card, booking-form)
    sections/                 (hero, discography, show-journey, merch-highlight, press-kit)
    lib/                      (api clients, formatting, auth helpers, i18n)
    styles/                   (theme, tokens, layout, accessibility helpers)
  package.json
  tsconfig.json
```

---

## 4. API SPEC (EXPLICIT, VERSIONED, TESTED)

Base URL: `https://api.6-empires.com/v1` (staging: `https://api-staging.6-empires.com/v1`). All endpoints are typed and versioned. Any breaking change creates a new version path.

### 4.1 Auth (shared across all brands)
* `POST /auth/login?provider=google|apple|spotify` — starts OAuth2 flow, returns redirect URL
* `GET /auth/callback?provider=...&code=...` — exchanges code for session tokens, sets cookies
* `GET /auth/me` — returns current user profile (id, name, email, role, brand access)
* `POST /auth/logout` — clears session, revokes refresh token

### 4.2 Artists and releases (Orchestra + Studios)
* `GET /artists` — optional `genre`, `spiritual_theme`, `language`, `page`, `limit`; returns paginated roster
* `POST /artists` — creates artist (label-only) with name, bio, genres, themes, social links, hero image, status
* `GET /artists/{artist_id}` — returns full artist profile with discography and booking state
* `POST /releases` — creates release (label-only) with type, title, date, streaming links, lyrics, credits
* `GET /releases?artist_id=...&type=...&limit=...` — returns paginated releases for an artist

### 4.3 Booking (AI-assisted)
* `POST /booking/request` — accepts event details (dates, venue type, capacity, budget, location, contact); returns draft agreement
* `GET /booking/availability?start=...&end=...&venue_type=...` — returns availability windows
* `GET /booking/contracts?event_id=...` — returns contract and rider documents (PDF links)

### 4.4 Merch (HighYogi integration)
* `GET /shop/products?collection=fashion|jewelry|art&page=...` — returns paginated products
* `POST /shop/orders` — creates order from cart with spiritual meaning metadata and limited-edition tracking
* `GET /shop/products/{product_id}/meaning` — returns the "meditation card" text and artwork details

### 4.5 Social and content (automation, analytics, publishing)
* `POST /smm/publish` — queues a post across selected platforms with per-platform text, hashtags, media
* `GET /smm/analytics?platform=...&period=...` — returns engagement, reach, conversion metrics
* `GET /releases/{release_id}/sync-status` — returns platform sync status (Spotify, Apple, YouTube)

### 4.6 AI layer (shared intelligence)
* `POST /ai/recommendations` — accepts context (artist, fan, content type), returns ranked recommendations
* `POST /ai/orchestration` — accepts stem or theme, returns generated arrangement, mastering settings, artwork prompts
* `POST /ai/booking-assistant` — accepts event brief, returns generated agreement, rider, logistics checklist

Contract testing: every endpoint has a schema (OpenAPI/TypeSpec), example requests, expected responses, error cases, and automated tests in CI. Devs do not ship endpoints without contract tests passing.

---

## 5. DATA MODELS (SCHEMA-READY, MULTI-LANG, SPIRITUAL METADATA)

### 5.1 Artist
```sql
CREATE TABLE artists (
  artist_id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  bio JSONB NOT NULL,              -- {en: "...", hy: "...", ru: "..."}
  genres TEXT[] NOT NULL,
  spiritual_themes TEXT[] NOT NULL,
  social_links JSONB NOT NULL,      -- {instagram: "...", tiktok: "...", youtube: "..."}
  hero_image_url TEXT NOT NULL,
  status TEXT NOT NULL,             -- active|touring|onboarding
  management JSONB NOT NULL,        -- {label: "...", agent: "...", contact: "..."}
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 5.2 Release
```sql
CREATE TABLE releases (
  release_id UUID PRIMARY KEY,
  artist_id UUID NOT NULL REFERENCES artists(artist_id),
  type TEXT NOT NULL,               -- album|single|video|live|ep
  title JSONB NOT NULL,             -- multi-lang
  release_date DATE NOT NULL,
  streaming_links JSONB NOT NULL,   -- spotify|apple|youtube URLs
  lyrics JSONB NOT NULL,            -- {original: "...", translations: {en: "...", hy: "...", ru: "..."}}
  credits JSONB NOT NULL,           -- [{role, name}]
  spirituality JSONB,               -- {theme: "...", meaning: "...", related_artwork: "..."}
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### 5.3 Event (tour/booking)
```sql
CREATE TABLE events (
  event_id UUID PRIMARY KEY,
  artist_id UUID NOT NULL REFERENCES artists(artist_id),
  name TEXT NOT NULL,
  venue JSONB NOT NULL,             -- {name, city, country, capacity, type}
  start_date TIMESTAMPTZ NOT NULL,
  end_date TIMESTAMPTZ NOT NULL,
  ticket_link TEXT,
  status TEXT NOT NULL,             -- announced|selling|sold_out|completed
  metadata JSONB                     -- {price_tiers, VIP_packages, meet_greet}
);
```

### 5.4 Product (HighYogi)
```sql
CREATE TABLE products (
  product_id UUID PRIMARY KEY,
  collection TEXT NOT NULL,          -- fashion|jewelry|art
  name TEXT NOT NULL,
  description JSONB NOT NULL,        -- multi-lang
  spiritual_meaning TEXT NOT NULL,
  limited_edition BOOLEAN NOT NULL,
  quantity_total INT NOT NULL,
  quantity_available INT NOT NULL,
  artist_royalty_pct DECIMAL(5,2) NOT NULL,
  images JSONB NOT NULL,             -- [{url, alt, type}]
  price JSONB NOT NULL,              -- {amount, currency, compare_at}
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### 5.5 Order (HighYogi + merch)
```sql
CREATE TABLE orders (
  order_id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  items JSONB NOT NULL,              -- [{product_id, qty, price_snapshot, meaning_card}]
  total DECIMAL(12,2) NOT NULL,
  currency TEXT NOT NULL,
  status TEXT NOT NULL,              -- pending|paid|fulfilled|cancelled|refunded
  payment_intent TEXT,               -- Stripe payment intent id
  shipping JSONB,                    -- address, tracking
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 5.6 Booking request (AI-assisted)
```sql
CREATE TABLE booking_requests (
  booking_id UUID PRIMARY KEY,
  artist_id UUID NOT NULL REFERENCES artists(artist_id),
  requester JSONB NOT NULL,          -- {name, email, org, phone}
  event_details JSONB NOT NULL,      -- proposed dates, venue type, location, budget, audience size, theme
  status TEXT NOT NULL,              -- draft|reviewed|accepted|rejected
  generated_docs JSONB,              -- {agreement_url, rider_url, logistics_url}
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### 5.7 Fan profile (for recommendations and loyalty)
```sql
CREATE TABLE fans (
  fan_id UUID PRIMARY KEY,
  user_id UUID,                       -- links to shared auth user
  preferred_languages TEXT[] NOT NULL,
  favorite_genres TEXT[],
  spiritual_interests TEXT[],
  created_at TIMESTAMPTZ DEFAULT now()
);
```

Contract testing: every model has migration scripts, seed data for dev, and validation rules enforced in code (e.g. `spiritual_meaning` required for HighYogi products; `status` transitions only via state machine for orders).

---

## 6. SCREEN / FLOW LIST (EXPLICIT, DEV-READY)

### 6.1 Public artist site (reincarnation.am)
Routes (Next.js pages):
* `/` — Hero (brand message, featured release, upcoming tour, spiritual quote)
* `/music` — Discography (grid of albums/singles with player, sync status, spiritual meaning card)
* `/music/[release_id]` — Release detail (player, lyrics in tabs, credits, related merch, recommendations)
* `/tour` — Tour list (dates, venues, tickets, VIP packages, show narrative)
* `/merch` — Shop (collections, spiritual meaning, limited edition badges, cart flow)
* `/about` — Story (mission, philosophy, press kit, gallery, video highlights)
* `/contact` — Contact (booking form, press inquiry, fan message, social links)

### 6.2 Booking flow (AI-assisted)
Flow steps:
1. User submits event brief (dates, venue type, budget, location, audience size, theme).
2. Backend generates draft agreement, rider, logistics checklist via `booking-ai-agent`.
3. Roland/managers review draft, edit, and send final version.
4. User signs digitally; system stores documents and updates booking status.

### 6.3 Merch purchase flow (HighYogi)
Flow steps:
1. Browse products by collection and meaning.
2. Add to cart (with quantity and edition tracking).
3. Checkout (shared auth, Stripe payment, shipping details).
4. Order confirmation (with meaning card, tracking, artist thank-you note).
5. Post-purchase engagement (email follow-up with exclusive content or early access).

### 6.4 Fan engagement flow (owned audience)
Flow steps:
1. Sign up or log in (social auth or email).
2. Preferences (language, genres, spiritual interests) captured and stored.
3. Personalized feed (releases, tour dates, merch drops, content) via AI recommendations.
4. Action tracking (streams, purchases, shares) feeds loyalty system (early access, discounts, VIP).

---

## 7. ACCEPTANCE CRITERIA (MEASURABLE, TESTABLE, CI-ENFORCED)

A pull request is only acceptable when ALL of the following pass:
* All endpoints have contract tests with example requests and expected responses (schema, auth, error cases).
* All pages render correctly in ENG/ARM/RUS with no layout breaks (visual regression tests in CI).
* All payments have fraud checks, 3DS where required, and rollback on failure (payment tests in CI with sandbox keys).
* All social publishing respects rate limits, retries with backoff, and logs failures to the team (integration tests with mocked APIs).
* All analytics events are captured (page views, clicks, purchases, streams) and stored in the analytics DB within 1 minute of event.
* All merch drops have limited-edition tracking, quantity enforcement, and meaning card generation (unit + e2e tests).

---

## 8. DEPLOYMENT, MONITORING, AND ROLLBACK (PRODUCTION-GRADE)

**Pipeline**: GitHub Actions → build → test (unit, integration, contract, visual, e2e) → deploy to staging → smoke tests → deploy to production (blue/green) → post-deploy monitoring.

**Monitoring**:
* Uptime checks on all public endpoints (5xx, latency, saturation) with alerts to on-call engineer.
* Error tracking (Sentry) with releases tagged and errors grouped by brand and feature.
* Business metrics (streams, sales, signups, conversion) dashboarded daily (Looker Studio or internal dashboard).

**Rollback**:
* Automated rollback on health-check failure within 2 minutes of deploy.
* Manual rollback via one-click script that restores previous build and clears CDN cache.
* Post-incident review with root cause, action items, and updated playbooks.

---

## 9. CREATIVE DELIVERABLES (ROLAND'S INPUT — TRACKED AS SCOPE)

These are inputs the dev team needs from Roland and his team, tracked as deliverables, not assumptions:
* Final tagline and brand voice (wording, tone, examples) for all brands
* Final color palette, fonts, imagery, and motion style (theme tokens in design system)
* First 10 HighYogi product concepts (name, image, spiritual meaning, limited edition count)
* Tour dates and venue list (6 months ahead) with VIP packages defined
* Booking package details (rider, agreement terms, logistics checklist) for the top 3 markets
* Social media campaign themes and content calendar (30 days ahead)
* Reference artists/creators for each brand (so devs understand what "feels right")

---

## 10. WHAT WE DO NEXT (AFTER YOUR APPROVAL)

Once you approve this spec, Hermes does the following in order:
1. Generate database migrations and seed data (dev environment)
2. Generate OpenAPI/TypeSpec contracts for all shared endpoints
3. Generate Next.js page and component skeletons for `reincarnation-orchestra` with design tokens and i18n
4. Generate FastAPI skeleton for `shared-backend` with auth, validation, and error handling
5. Generate CI/CD pipeline (GitHub Actions) with test stages, staging deploy, production deploy, rollback
6. Generate monitoring dashboards and alert rules (uptime, errors, business metrics)

You then hand these artifacts to the dev team as the single source of truth. Any change request goes through you (Roland) and Hermes, and is versioned (v1.1, v1.2, etc.).

Version: 1.0 | Approved by Roland: [signature] | Approved by Hermes: [signature] | Date: 2026-10-10
