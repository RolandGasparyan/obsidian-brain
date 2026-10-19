---
title: Reincarnation Orchestra — Project Hub
type: moc
tags: [music, orchestra, reincarnation, music-video, generation, absolute]
created: 2026-10-18
updated: 2026-10-18
---

# 🎵 Reincarnation Orchestra — Project Hub

> The flagship brand. Armenian heritage fused with modern cosmic sound. **"When Music Heals the Soul."**
> Standard: **ABSOLUTE** — music already achieved it; the generation pipeline and platform must equal it.

---

## 📄 Documents in this folder

| Document | What it is | Status |
|---|---|---|
| [[GENERATING-MUSIC-AND-VIDEO-BLUEPRINT-v1.0]] | **Unified Music + Video generation pipeline** — job model, API contract, stage code, gates, acceptance criteria | ✅ SPEC READY (dev-executable) |
| [[REINCARNATION-ORCHESTRA-SPEC-v1.0]] | Vision · business · tech · API · data · screens · KPIs | ✅ v1.0 |
| [[IMPLEMENTATION-SKELETON]] | DB migrations, seed data, OpenAPI, Next.js + FastAPI skeletons, CI/CD, Grafana | ✅ v1.0 |
| [[EMPIRE-SPEC-FOR-DEV-TEAM]] | Empire-wide architecture (all brands on one backend) | ✅ v1.0 |

> These three were written 2026-10-10 into a temporary Hermes workspace, auto-pruned after 24 h, and **restored verbatim from the session record on 2026-10-18**. They now live here permanently and are version-controlled.

---

## 🔌 Where the real code lives

| Layer | Repo | Verified capability |
|---|---|---|
| Video generation | `RolandGasparyan/vortex` | `POST /api/video/generate` → LTX-Video via `cog` / `replicate` / `fal`; `deploy/video-cog/` |
| Music generation | `RolandGasparyan/REINCARNATION-Social-media-Gods` | `npm run music:lyria` → Google **Lyria 3 Pro** via OpenRouter (SSE, base64 audio deltas) |
| Social automation | `RolandGasparyan/reincarnation-smm` | Trinity egregor daemon, Postiz scheduling, trilogy prompts |
| Label / roster backend | — | spec only (see IMPLEMENTATION-SKELETON) |

---

## 🎯 Status

| Layer | Status |
|---|---|
| Music | ✅ ABSOLUTE (30–40 awards · 8 albums · 24+ years) |
| Music generation (Lyria) | ✅ working script |
| Video generation (LTX) | ✅ working client + Cog deploy |
| **Unified music→video job** | 📋 blueprint ready — **not built yet** |
| Artist platform | 📋 spec ready |
| Booking AI / SMM | 🔄 exists, needs upgrade |

---

## ▶️ Next actions

- [ ] Hand `GENERATING-MUSIC-AND-VIDEO-BLUEPRINT-v1.0` to the dev team — 5 new files in `vortex`, no new repo
- [ ] Verify `FFMPEG_BIN` + run §10 Test 2 (music only) — cheapest first proof
- [ ] Roland answers §15 open questions (brand look, voice, languages, aspect, approval gate)
- [ ] First real job: one 60 s Reincarnation piece end-to-end into `VORTEX-Outputs/jobs/`
- [ ] After that: 9:16 reels auto-derived + marketing pack → Postiz queue (human approval)

---

_Part of [[ABSOLUTE_BRAIN]] — maintained by Hermes Agent._
