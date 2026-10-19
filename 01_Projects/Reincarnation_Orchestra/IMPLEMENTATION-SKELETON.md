# REINCARNATION ORCHESTRA — IMPLEMENTATION SKELETON FOR DEV TEAM

Version: 1.0 | Date: 2026-10-10 | Owner: Roland Gasparyan (Artist/Director) | Architect: Hermes
Rule: This file, along with REINCARNATION-ORCHESTRA-SPEC-v1.0.md, is the single source of truth. Devs build ONLY from these docs. Any change is versioned by Roland/Hermes — no ad-hoc decisions in code.

---

## 1. DATABASE MIGRATIONS (PostgreSQL)

Save as `/migrations/001_initial_schema.sql`

```sql
-- Enable UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Artists table
CREATE TABLE artists (
  artist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  bio JSONB NOT NULL,                       -- {"en": "...", "hy": "...", "ru": "..."}
  genres TEXT[] NOT NULL,
  spiritual_themes TEXT[] NOT NULL,
  social_links JSONB NOT NULL,               -- {"instagram": "...", "tiktok": "...", "youtube": "..."}
  hero_image_url TEXT NOT NULL,
  status TEXT NOT NULL,                      -- active|touring|onboarding
  management JSONB NOT NULL,                 -- {"label": "...", "agent": "...", "contact": "..."}
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Releases table
CREATE TABLE releases (
  release_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  artist_id UUID NOT NULL REFERENCES artists(artist_id) ON DELETE CASCADE,
  type TEXT NOT NULL,                        -- album|single|video|live|ep
  title JSONB NOT NULL,                      -- multi-lang
  release_date DATE NOT NULL,
  streaming_links JSONB NOT NULL,            -- {"spotify": "...", "apple": "...", "youtube": "..."}
  lyrics JSONB NOT NULL,                    -- {"original": "...", "translations": {"en": "...", "hy": "...", "ru": "..."}}
  credits JSONB NOT NULL,                    -- [{"role": "producer", "name": "..."}]
  spirituality JSONB,                        -- {"theme": "...", "meaning": "...", "related_artwork": "..."}
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Events table (tour/booking)
CREATE TABLE events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  artist_id UUID NOT NULL REFERENCES artists(artist_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  venue JSONB NOT NULL,                      -- {"name": "...", "city": "...", "country": "...", "capacity": N, "type": "..."}
  start_date TIMESTAMPTZ NOT NULL,
  end_date TIMESTAMPTZ NOT NULL,
  ticket_link TEXT,
  status TEXT NOT NULL,                      -- announced|selling|sold_out|completed
  metadata JSONB,                            -- {"price_tiers": [...], "VIP_packages": [...], "meet_greet": bool}
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Products table (HighYogi)
CREATE TABLE products (
  product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  collection TEXT NOT NULL,                   -- fashion|jewelry|art
  name TEXT NOT NULL,
  description JSONB NOT NULL,                 -- multi-lang
  spiritual_meaning TEXT NOT NULL,
  limited_edition BOOLEAN NOT NULL,
  quantity_total INT NOT NULL,
  quantity_available INT NOT NULL,
  artist_royalty_pct DECIMAL(5,2) NOT NULL,
  images JSONB NOT NULL,                      -- [{"url": "...", "alt": "...", "type": "..."}]
  price JSONB NOT NULL,                       -- {"amount": N, "currency": "...", "compare_at": N}
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Orders table (HighYogi + merch)
CREATE TABLE orders (
  order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  items JSONB NOT NULL,                       -- [{"product_id": uuid, "qty": N, "price_snapshot": {...}, "meaning_card": "..."}]
  total DECIMAL(12,2) NOT NULL,
  currency TEXT NOT NULL,
  status TEXT NOT NULL,                       -- pending|paid|fulfilled|cancelled|refunded
  payment_intent TEXT,                        -- Stripe payment intent id
  shipping JSONB,                             -- {"address": {...}, "tracking": "..."}
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Booking requests table (AI-assisted)
CREATE TABLE booking_requests (
  booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  artist_id UUID NOT NULL REFERENCES artists(artist_id) ON DELETE CASCADE,
  requester JSONB NOT NULL,                   -- {"name": "...", "email": "...", "org": "...", "phone": "..."}
  event_details JSONB NOT NULL,                -- {"dates": [...], "venue_type": "...", "location": "...", "budget": N, "audience_size": N, "theme": "..."}
  status TEXT NOT NULL,                       -- draft|reviewed|accepted|rejected
  generated_docs JSONB,                        -- {"agreement_url": "...", "rider_url": "...", "logistics_url": "..."}
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Fans table (for recommendations and loyalty)
CREATE TABLE fans (
  fan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,                                -- links to shared auth user
  preferred_languages TEXT[] NOT NULL DEFAULT '{"en","hy","ru"}',
  favorite_genres TEXT[] DEFAULT '{}',
  spiritual_interests TEXT[] DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for performance
CREATE INDEX idx_releases_artist_id ON releases(artist_id);
CREATE INDEX idx_events_artist_id ON events(artist_id);
CREATE INDEX idx_events_dates ON events(start_date, end_date);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_booking_requests_artist_id ON booking_requests(artist_id);
CREATE INDEX idx_products_collection ON products(collection);
```

---

## 2. SEED DATA (Dev Environment)

Save as `/seeds/dev_seed.sql`

```sql
-- Insert Reincarnation Orchestra artist
INSERT INTO artists (name, bio, genres, spiritual_themes, social_links, hero_image_url, status, management)
VALUES (
  'Reincarnation Orchestra',
  '{"en": "A spiritual music collective blending Armenian heritage with modern cosmic sounds.", "hy": "Հոգևոր երաժշտական կոլեկտիվ, որը միավորում է հայկական ժառանգությունը ժամանակակից կոսմիկ ձայնների հետ:", "ru": "Духовный музыкальный коллектив, объединяющий армянское наследие с современными космическими звуками."}',
  '{"symphonic metal", "world fusion", "spiritual rock", "cinematic"}',
  '{"healing", "unity", "transformation", "Armenian heritage", "cosmic"}',
  '{"instagram": "@reincarnationorchestra", "tiktok": "@reincarnationorchestra", "youtube": "ReincarnationOrchestra"}',
  '/images/reincarnation-hero.jpg',
  'active',
  '{"label": "Reincarnation Studios", "agent": "Roland Gasparyan", "contact": "booking@reincarnationstudios.com"}'
);

-- Insert first album
INSERT INTO releases (artist_id, type, title, release_date, streaming_links, lyrics, credits, spirituality)
VALUES (
  (SELECT artist_id FROM artists WHERE name = 'Reincarnation Orchestra'),
  'album',
  '{"en": "When Music Heals the Soul", "hy": "Երբ երաժշտությունը բուժում է հոգին", "ru": "Когда музыка исцеляет душу"}',
  '2026-11-20',
  '{"spotify": "https://open.spotify.com/album/...", "apple": "https://music.apple.com/album/...", "youtube": "https://youtube.com/playlist?list=..."}',
  '{"original": "When the strings cry out for healing...", "translations": {"en": "...", "hy": "...", "ru": "..."}}',
  '[{"role": "composer", "name": "Roland Gasparyan"}, {"role": "producer", "name": "Roland Gasparyan"}, {"role": "lyricist", "name": "Roland Gasparyan"}]',
  '{"theme": "healing through Armenian cosmic sound", "meaning": "Each song is a portal to inner transformation.", "related_artwork": "cosmic-armenian-mandala.png"}'
);

-- Insert first tour stop
INSERT INTO events (artist_id, name, venue, start_date, end_date, ticket_link, status, metadata)
VALUES (
  (SELECT artist_id FROM artists WHERE name = 'Reincarnation Orchestra'),
  'Reincarnation Orchestra — World Tour 2026',
  '{"name": "Yerevan Opera Theatre", "city": "Yerevan", "country": "Armenia", "capacity": 1200, "type": "opera_house"}',
  '2026-12-05 20:00:00+04',
  '2026-12-05 22:30:00+04',
  'https://ticketing.reincarnation.am/yerevan-2026',
  'announced',
  '{"price_tiers": [{"name": "General", "price": 50}, {"name": "VIP", "price": 150}], "VIP_packages": [{"name": "Meet & Greet", "perks": ["photo", "signed poster"]}], "meet_greet": true}'
);

-- Insert first HighYogi product
INSERT INTO products (collection, name, description, spiritual_meaning, limited_edition, quantity_total, quantity_available, artist_royalty_pct, images, price)
VALUES (
  'art',
  'Cosmic Armenian Mandala',
  '{"en": "A limited-edition art piece inspired by Armenian spiritual geometry.", "hy": "Սահմանափակ թողարկում արվեստ, ոգեշնչված հայկական հոգևոր երկրաչափությամբ:", "ru": "Ограниченный тираж искусства, вдохновленного армянской духовной геометрией."}',
  'This mandala represents the harmony of cosmic energies and Armenian spiritual tradition. Meditate with it to align your inner self.',
  true, 100, 100,
  0.15,
  '[{"url": "/images/mandala-1.jpg", "alt": "Cosmic Armenian Mandala", "type": "front"}]',
  '{"amount": 500, "currency": "USD", "compare_at": 800}'
);
```

---

## 3. API CONTRACT (OpenAPI Skeleton)

Save as `/contracts/openapi.yaml`

```yaml
openapi: 3.0.3
info:
  title: 6-empires Unified API
  version: 1.0.0
  description: Shared API for Reincarnation Orchestra, Studios, HighYogi, Trading Guru
servers:
  - url: https://api.6-empires.com/v1
    description: Production
  - url: https://api-staging.6-empires.com/v1
    description: Staging
paths:
  /auth/login:
    post:
      summary: Start OAuth2 flow
      parameters:
        - name: provider
          in: query
          required: true
          schema:
            type: string
            enum: [google, apple, spotify]
      responses:
        '200':
          description: Redirect URL for OAuth2
          content:
            application/json:
              schema:
                type: object
                properties:
                  redirect_url:
                    type: string
                    format: uri
  /auth/me:
    get:
      summary: Get current user
      security:
        - bearerAuth: []
      responses:
        '200':
          description: User profile
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: string
                    format: uuid
                  name:
                    type: string
                  email:
                    type: string
                    format: email
                  role:
                    type: string
                    enum: [fan, artist, manager, admin]
                  brand_access:
                    type: array
                    items:
                      type: string
                      enum: [reincarnation, studios, highyogi, trading_guru]
  /artists:
    get:
      summary: List artists
      parameters:
        - name: genre
          in: query
          schema:
            type: string
        - name: spiritual_theme
          in: query
          schema:
            type: string
        - name: language
          in: query
          schema:
            type: string
            enum: [en, hy, ru]
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: Paginated artists
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Artist'
                  page:
                    type: integer
                  limit:
                    type: integer
                  total:
                    type: integer
    post:
      summary: Create artist (label-only)
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ArtistInput'
      responses:
        '201':
          description: Artist created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Artist'
  /releases:
    get:
      summary: List releases for an artist
      parameters:
        - name: artist_id
          in: query
          required: true
          schema:
            type: string
            format: uuid
        - name: type
          in: query
          schema:
            type: string
            enum: [album, single, video, live, ep]
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: Paginated releases
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Release'
                  page:
                    type: integer
                  limit:
                    type: integer
                  total:
                    type: integer
    post:
      summary: Create release (label-only)
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ReleaseInput'
      responses:
        '201':
          description: Release created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Release'
  /booking/request:
    post:
      summary: Submit booking request
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                artist_id:
                  type: string
                  format: uuid
                event_details:
                  type: object
                  properties:
                    dates:
                      type: array
                      items:
                        type: string
                        format: date
                    venue_type:
                      type: string
                    location:
                      type: string
                    budget:
                      type: number
                    audience_size:
                      type: integer
                    theme:
                      type: string
      responses:
        '200':
          description: Draft agreement generated
          content:
            application/json:
              schema:
                type: object
                properties:
                  booking_id:
                    type: string
                    format: uuid
                  status:
                    type: string
                    enum: [draft, reviewed, accepted, rejected]
                  generated_docs:
                    type: object
                    properties:
                      agreement_url:
                        type: string
                        format: uri
                      rider_url:
                        type: string
                        format: uri
                      logistics_url:
                        type: string
                        format: uri
  /shop/products:
    get:
      summary: List products
      parameters:
        - name: collection
          in: query
          schema:
            type: string
            enum: [fashion, jewelry, art]
        - name: page
          in: query
          schema:
            type: integer
            default: 1
      responses:
        '200':
          description: Paginated products
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Product'
                  page:
                    type: integer
                  limit:
                    type: integer
                  total:
                    type: integer
components:
  schemas:
    Artist:
      type: object
      properties:
        artist_id:
          type: string
          format: uuid
        name:
          type: string
        bio:
          type: object
          properties:
            en:
              type: string
            hy:
              type: string
            ru:
              type: string
        genres:
          type: array
          items:
            type: string
        spiritual_themes:
          type: array
          items:
            type: string
        social_links:
          type: object
          properties:
            instagram:
              type: string
            tiktok:
              type: string
            youtube:
              type: string
        hero_image_url:
          type: string
          format: uri
        status:
          type: string
          enum: [active, touring, onboarding]
        management:
          type: object
          properties:
            label:
              type: string
            agent:
              type: string
            contact:
              type: string
              format: email
    ArtistInput:
      type: object
      properties:
        name:
          type: string
        bio:
          type: object
          properties:
            en:
              type: string
            hy:
              type: string
            ru:
              type: string
        genres:
          type: array
          items:
            type: string
        spiritual_themes:
          type: array
          items:
            type: string
        social_links:
          type: object
          properties:
            instagram:
              type: string
            tiktok:
              type: string
            youtube:
              type: string
        hero_image_url:
          type: string
          format: uri
        status:
          type: string
          enum: [active, touring, onboarding]
        management:
          type: object
          properties:
            label:
              type: string
            agent:
              type: string
            contact:
              type: string
              format: email
    Release:
      type: object
      properties:
        release_id:
          type: string
          format: uuid
        artist_id:
          type: string
          format: uuid
        type:
          type: string
          enum: [album, single, video, live, ep]
        title:
          type: object
          properties:
            en:
              type: string
            hy:
              type: string
            ru:
              type: string
        release_date:
          type: string
          format: date
        streaming_links:
          type: object
          properties:
            spotify:
              type: string
              format: uri
            apple:
              type: string
              format: uri
            youtube:
              type: string
              format: uri
        lyrics:
          type: object
          properties:
            original:
              type: string
            translations:
              type: object
              properties:
                en:
                  type: string
                hy:
                  type: string
                ru:
                  type: string
        credits:
          type: array
          items:
            type: object
            properties:
              role:
                type: string
              name:
                type: string
        spirituality:
          type: object
          properties:
            theme:
              type: string
            meaning:
              type: string
            related_artwork:
              type: string
    ReleaseInput:
      type: object
      properties:
        artist_id:
          type: string
          format: uuid
        type:
          type: string
          enum: [album, single, video, live, ep]
        title:
          type: object
          properties:
            en:
              type: string
            hy:
              type: string
            ru:
              type: string
        release_date:
          type: string
          format: date
        streaming_links:
          type: object
          properties:
            spotify:
              type: string
              format: uri
            apple:
              type: string
              format: uri
            youtube:
              type: string
              format: uri
        lyrics:
          type: object
          properties:
            original:
              type: string
            translations:
              type: object
              properties:
                en:
                  type: string
                hy:
                  type: string
                ru:
                  type: string
        credits:
          type: array
          items:
            type: object
            properties:
              role:
                type: string
              name:
                type: string
        spirituality:
          type: object
          properties:
            theme:
              type: string
            meaning:
              type: string
            related_artwork:
              type: string
    Product:
      type: object
      properties:
        product_id:
          type: string
          format: uuid
        collection:
          type: string
          enum: [fashion, jewelry, art]
        name:
          type: string
        description:
          type: object
          properties:
            en:
              type: string
            hy:
              type: string
            ru:
              type: string
        spiritual_meaning:
          type: string
        limited_edition:
          type: boolean
        quantity_total:
          type: integer
        quantity_available:
          type: integer
        artist_royalty_pct:
          type: number
          format: float
        images:
          type: array
          items:
            type: object
            properties:
              url:
                type: string
                format: uri
              alt:
                type: string
              type:
                type: string
        price:
          type: object
          properties:
            amount:
              type: number
            currency:
              type: string
            compare_at:
              type: number
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

---

## 4. NEXT.JS SKELETON (reincarnation-orchestra)

Save as `/apps/reincarnation-orchestra/package.json`

```json
{
  "name": "reincarnation-orchestra",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "next": "14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.0.0",
    "axios": "^1.6.0",
    "next-intl": "^3.0.0",
    "tailwindcss": "^3.3.0",
    "framer-motion": "^10.16.0",
    "react-player": "^2.13.0",
    "stripe": "^13.0.0",
    "zustand": "^4.4.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.2.0",
    "jest": "^29.7.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/jest-dom": "^5.17.0",
    "playwright": "^1.39.0",
    "eslint": "^8.52.0",
    "eslint-config-next": "14.0.0",
    "prettier": "^3.0.0"
  }
}
```

Save as `/apps/reincarnation-orchestra/next.config.js`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  i18n: {
    locales: ['en', 'hy', 'ru'],
    defaultLocale: 'en',
  },
  images: {
    domains: ['api.6-empires.com', 'cdn.reincarnation.am'],
    formats: ['image/avif', 'image/webp'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'https://api.6-empires.com/v1/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
```

Save as `/apps/reincarnation-orchestra/src/pages/index.tsx`

```tsx
import { GetStaticProps } from 'next';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import Image from 'next/image';

interface HomeProps {
  featuredRelease: any;
  upcomingEvents: any[];
  featuredProducts: any[];
}

export const getStaticProps: GetStaticProps = async ({ locale }) => {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/releases?artist_id=reincarnation-orchestra&type=album&limit=1`);
  const featuredRelease = await res.json();

  const eventsRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/events?artist_id=reincarnation-orchestra&limit=3`);
  const upcomingEvents = await eventsRes.json();

  const productsRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/shop/products?collection=art&limit=4`);
  const featuredProducts = await productsRes.json();

  return {
    props: {
      featuredRelease: featuredRelease.data[0],
      upcomingEvents: upcomingEvents.data,
      featuredProducts: featuredProducts.data,
      messages: (await import(`../messages/${locale}.json`)).default,
    },
    revalidate: 60,
  };
};

export default function Home({ featuredRelease, upcomingEvents, featuredProducts }: HomeProps) {
  const t = useTranslations('home');

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Hero Section */}
      <section className="relative h-screen flex items-center justify-center">
        <div className="absolute inset-0 bg-gradient-to-b from-purple-900/20 to-black" />
        <div className="relative z-10 text-center max-w-4xl px-4">
          <h1 className="text-6xl font-bold mb-4 text-gold">
            {t('hero.title')}
          </h1>
          <p className="text-2xl mb-8 text-gray-300">
            {t('hero.subtitle')}
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/music" className="bg-purple-600 hover:bg-purple-700 px-8 py-3 rounded-full">
              {t('hero.listen_now')}
            </Link>
            <Link href="/tour" className="border border-gold text-gold hover:bg-gold hover:text-black px-8 py-3 rounded-full">
              {t('hero.view_tour')}
            </Link>
          </div>
        </div>
      </section>

      {/* Featured Release */}
      {featuredRelease && (
        <section className="py-20 px-4 max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold mb-8 text-center">{t('featured_release')}</h2>
          <div className="bg-gray-900 rounded-2xl p-8 flex flex-col md:flex-row gap-8">
            <div className="flex-shrink-0">
              <Image
                src={featuredRelease.images?.[0]?.url || '/placeholder-album.png'}
                alt={featuredRelease.title?.[locale]}
                width={400}
                height={400}
                className="rounded-lg"
              />
            </div>
            <div className="flex-1">
              <h3 className="text-3xl font-bold mb-4">{featuredRelease.title?.[locale]}</h3>
              <p className="text-gray-300 mb-6">{featuredRelease.spirituality?.meaning}</p>
              <div className="flex gap-4">
                <a href={featuredRelease.streaming_links?.spotify} target="_blank" rel="noopener" className="bg-green-600 px-6 py-2 rounded-full">
                  Spotify
                </a>
                <a href={featuredRelease.streaming_links?.apple} target="_blank" rel="noopener" className="bg-gray-700 px-6 py-2 rounded-full">
                  Apple Music
                </a>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Upcoming Events */}
      <section className="py-20 px-4 max-w-6xl mx-auto">
        <h2 className="text-4xl font-bold mb-8 text-center">{t('upcoming_tour')}</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {upcomingEvents.map((event) => (
            <div key={event.event_id} className="bg-gray-900 rounded-xl p-6">
              <h3 className="text-xl font-bold mb-2">{event.name}</h3>
              <p className="text-gray-300 mb-2">{event.venue.city}, {event.venue.country}</p>
              <p className="text-gold mb-4">{new Date(event.start_date).toLocaleDateString()}</p>
              <a href={event.ticket_link} target="_blank" rel="noopener" className="block text-center bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-full">
                {t('get_tickets')}
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* Featured Products */}
      <section className="py-20 px-4 max-w-6xl mx-auto">
        <h2 className="text-4xl font-bold mb-8 text-center">{t('limited_edition')}</h2>
        <div className="grid md:grid-cols-4 gap-6">
          {featuredProducts.map((product) => (
            <div key={product.product_id} className="bg-gray-900 rounded-xl p-4">
              <Image
                src={product.images?.[0]?.url || '/placeholder-product.png'}
                alt={product.name}
                width={300}
                height={300}
                className="rounded-lg mb-4"
              />
              <h3 className="text-lg font-bold mb-2">{product.name}</h3>
              <p className="text-sm text-gray-300 mb-2">{product.spiritual_meaning}</p>
              <p className="text-gold font-bold">${product.price?.amount}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
```

---

## 5. FASTAPI SKELETON (shared-backend)

Save as `/apps/shared-backend/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uuid
from datetime import datetime
import os

app = FastAPI(title="6-empires Unified API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://reincarnation.am", "https://staging.reincarnation.am"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Database (placeholder - use SQLAlchemy or similar)
from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Boolean, Integer, Numeric, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

engine = create_engine(os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/6empires"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Artist(Base):
    __tablename__ = "artists"
    artist_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    bio = Column(JSONB, nullable=False)
    genres = Column(ARRAY(String), nullable=False)
    spiritual_themes = Column(ARRAY(String), nullable=False)
    social_links = Column(JSONB, nullable=False)
    hero_image_url = Column(String, nullable=False)
    status = Column(String, nullable=False)
    management = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Release(Base):
    __tablename__ = "releases"
    release_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artist_id = Column(UUID(as_uuid=True), ForeignKey("artists.artist_id"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(JSONB, nullable=False)
    release_date = Column(DateTime, nullable=False)
    streaming_links = Column(JSONB, nullable=False)
    lyrics = Column(JSONB, nullable=False)
    credits = Column(JSONB, nullable=False)
    spirituality = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Validate JWT token here
    return credentials.credentials

# Auth routes
@app.post("/auth/login")
async def login(provider: str):
    if provider not in ["google", "apple", "spotify"]:
        raise HTTPException(status_code=400, detail="Invalid provider")
    # OAuth2 flow implementation
    return {"redirect_url": f"https://{provider}.com/oauth?redirect_uri=..."}

@app.get("/auth/me")
async def get_me(token: str = Depends(get_current_user)):
    # Return user profile
    return {"user_id": "uuid", "name": "Roland", "email": "roland@6empires.com", "role": "admin", "brand_access": ["reincarnation", "studios", "highyogi", "trading_guru"]}

# Artists routes
@app.get("/artists")
async def list_artists(
    genre: Optional[str] = None,
    spiritual_theme: Optional[str] = None,
    language: Optional[str] = "en",
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(Artist)
    if genre:
        query = query.filter(Artist.genres.contains([genre]))
    if spiritual_theme:
        query = query.filter(Artist.spiritual_themes.contains([spiritual_theme]))
    
    total = query.count()
    artists = query.offset((page-1)*limit).limit(limit).all()
    
    return {"data": artists, "page": page, "limit": limit, "total": total}

@app.post("/artists")
async def create_artist(
    artist: dict,
    token: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate label role
    new_artist = Artist(**artist)
    db.add(new_artist)
    db.commit()
    db.refresh(new_artist)
    return new_artist

# Releases routes
@app.get("/releases")
async def list_releases(
    artist_id: str,
    type: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(Release).filter(Release.artist_id == artist_id)
    if type:
        query = query.filter(Release.type == type)
    
    releases = query.limit(limit).all()
    return {"data": releases, "page": 1, "limit": limit, "total": len(releases)}

# Booking routes
@app.post("/booking/request")
async def create_booking_request(
    booking: dict,
    db: Session = Depends(get_db)
):
    # Generate draft agreement via AI
    booking_id = str(uuid.uuid4())
    return {
        "booking_id": booking_id,
        "status": "draft",
        "generated_docs": {
            "agreement_url": f"/docs/{booking_id}/agreement.pdf",
            "rider_url": f"/docs/{booking_id}/rider.pdf",
            "logistics_url": f"/docs/{booking_id}/logistics.pdf"
        }
    }

# Products routes (HighYogi)
@app.get("/shop/products")
async def list_products(
    collection: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    # Mock data for now
    return {
        "data": [
            {
                "product_id": str(uuid.uuid4()),
                "collection": "art",
                "name": "Cosmic Armenian Mandala",
                "spiritual_meaning": "This mandala represents harmony...",
                "limited_edition": True,
                "quantity_total": 100,
                "quantity_available": 100,
                "price": {"amount": 500, "currency": "USD"}
            }
        ],
        "page": page,
        "limit": 20,
        "total": 1
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 6. CI/CD PIPELINE (GitHub Actions)

Save as `/.github/workflows/deploy.yml`

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  NODE_VERSION: '20'
  PYTHON_VERSION: '3.11'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Install dependencies
        run: |
          npm ci
          pip install -r requirements.txt
          
      - name: Run unit tests
        run: |
          npm test
          pytest
          
      - name: Run contract tests
        run: |
          npm run test:contract
          
      - name: Run visual regression tests
        run: |
          npm run test:visual
          
      - name: Run e2e tests
        run: |
          npm run test:e2e

  deploy-staging:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to staging
        run: |
          echo "Deploying to staging..."
          # Deploy commands here
          
      - name: Run smoke tests
        run: |
          echo "Running smoke tests..."

  deploy-production:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to production (blue/green)
        run: |
          echo "Deploying to production..."
          # Blue/green deploy commands here
          
      - name: Health check
        run: |
          echo "Running health checks..."
          curl -f https://api.6-empires.com/health || exit 1
          
      - name: Rollback on failure
        run: |
          echo "Rollback if needed..."
```

---

## 7. MONITORING DASHBOARD (Grafana Config)

Save as `/monitoring/grafana-dashboard.json`

```json
{
  "dashboard": {
    "title": "6-empires System Overview",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          }
        ]
      },
      {
        "title": "Active Users",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(user_active_total[1h]))",
            "legendFormat": "Users"
          }
        ]
      },
      {
        "title": "Revenue Tracking",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(order_total_amount[1h]))",
            "legendFormat": "Orders"
          }
        ]
      },
      {
        "title": "Streaming Metrics",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(stream_plays_total[1h]))",
            "legendFormat": "Streams"
          }
        ]
      }
    ]
  }
}
```

---

## 8. DELIVERABLES FOR THE DEV TEAM

Provide these files to the dev team as the single source of truth:

1. `/migrations/001_initial_schema.sql` - Database migrations
2. `/seeds/dev_seed.sql` - Seed data for dev
3. `/contracts/openapi.yaml` - API contract
4. `/apps/reincarnation-orchestra/` - Next.js skeleton
5. `/apps/shared-backend/` - FastAPI skeleton
6. `/.github/workflows/deploy.yml` - CI/CD pipeline
7. `/monitoring/grafana-dashboard.json` - Monitoring config
8. `REINCARNATION-ORCHESTRA-SPEC-v1.0.md` - Full specification
9. `EMPIRE-SPEC-FOR-DEV-TEAM.md` - Overall empire architecture

Rule: Any change request goes through Roland/Hermes and is versioned (v1.1, v1.2, etc.). Devs do not make ad-hoc decisions.

Version: 1.0 | Approved by Roland: [signature] | Approved by Hermes: [signature] | Date: 2026-10-10