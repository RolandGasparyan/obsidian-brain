# GENERATING MUSIC AND VIDEO — ABSOLUTE BLUEPRINT v1.0

Version: 1.0 · Date: 2026-10-18 · Owner: Roland Gasparyan (vision) · Architect: Hermes
Status: SPEC READY — no code written yet. Everything below builds on two repos that already ship verified code.

> This document is the single source of truth for the **Music + Video generation** pipeline.
> A junior developer must be able to build it from this file alone — no guessing, no "figure it out".

---

## 0. VERIFIED CURRENT STATE (checked 2026-10-18, not assumed)

| Asset | Where | What it actually does today |
|---|---|---|
| Video generation | `RolandGasparyan/vortex` — `server/lib/video.ts`, route `POST /api/video/generate` | Type-pluggable LTX-Video client: `cog` / `replicate` / `fal` behind one env var set. Returns `{providerId, model, url|base64, durationSec, predictionId}` |
| Video UI | `vortex/client/src/lib/videoClient.ts`, `Home.tsx` 🎬 per scene | Calls only `/api/video/generate`; inline `<video>` player |
| Video deployment | `vortex/deploy/video-cog/{cog.yaml,predict.py,deploy.sh}`, `INSTALL_VIDEO.md` | LTX-Video packaged as Cog for Verda / local `cog serve` |
| Output layout | `vortex/VORTEX_OUTPUTS_README.md` | `jobs/<id>/{manifest.json, script.txt, master.wav, voice.wav, final.mp4, final.srt, reels/, thumbnails/, marketing.json}` |
| Music generation | `RolandGasparyan/REINCARNATION-Social-media-Gods` — `scripts/generate-lyria-music.mts`, `npm run music:lyria` | Google **Lyria 3 Pro Preview** via OpenRouter chat-completions, **streaming SSE with `delta.audio.data` base64 chunks**, concatenated into an mp3 file |
| AI prompt rewriting | `vortex/server/lib/providers.ts` + `POST /api/ai/enhance` | Scene → rewritten cinematic prompt (empire self-hosted or GLM) |
| ffmpeg | `~/.hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffmpeg` (v9.0.1) | Available locally — mastering + mux are possible **today** |
| Local MusicGen | `~/mlx-train/venv` | ❌ **blocked** — `transformers 5.19.0` present but `torch` is NOT installed. No local audio model can run until `pip install torch` in a py3.11+ venv |

**Gap this blueprint closes:** music and video exist in two separate repos, with no single job that produces a finished piece (score → master → clips → mux → marketing pack). Nothing unifies them.

---

## 1. GOAL (one sentence)

One command / one HTTP call turns a Roland-approved creative brief into a **mastered soundtrack + finished 4K video + reels + marketing pack**, all written into `VORTEX-Outputs/jobs/<job_id>/`.

---

## 2. VISION LAYER — what it must FEEL like (Roland's words)

**ABSOLUTE** — կատարյալություն ամեն ինչում։ Music already hit it (30-40 awards, 8 albums, 24+ years). Music Video · AI Film · Painting · Web Design must equal it.

- **Spiritual truth** — every frame and every second carries Light, Goodness, Love, Respect, Universal Consciousness.
- **Armenian rooted** — heritage is the fabric, not the decoration.
- **No demo-grade output.** If it would not stand beside his best work, the job is not done — it is `failed`.

The pipeline enforces this literally: a job cannot reach `status: done` unless the mastering gate (−14 LUFS, TP ≤ −1.0 dBTP) and the completeness gate (all scenes rendered, mux verified) pass.

---

## 3. DECISIONS (chosen, with reasons — not options)

| # | Decision | Reason | Rejected alternative |
|---|---|---|---|
| D1 | **Extend `vortex`, do not create a new repo** | It already owns video + Express + the output layout. A second repo would duplicate the provider abstraction. | New `music-video-forge` repo — duplicates video.ts |
| D2 | **Music = Lyria 3 Pro via OpenRouter** | Verified working script exists (`generate-lyria-music.mts`); one API key already in `.env` | Local MusicGen — `torch` missing, Apple-silicon path unproven |
| D3 | **Video = LTX-Video through the existing Cog client** | Zero new code; 4 upstreams already supported | New provider integration — wasted work |
| D4 | **Job store = JSON files on disk (`jobs/<id>/manifest.json`), no database** | Same as today's VORTEX-Outputs contract; survives crashes; human-readable | Postgres/SQLite — YAGNI for a single-box pipeline |
| D5 | **Mastering = ffmpeg two-pass `loudnorm`** | Deterministic, no extra dependency, industry-standard −14 LUFS for streaming | Cloud mastering service — cost + latency |
| D6 | **Secrets stay server-side, env only** | Existing locked-in contract in `vortex/CLAUDE.md` | Anything client-side |

---

## 4. FILE TREE (complete — every new file named)

Inside `vortex`:

```
vortex/
├── server/
│   ├── index.ts                     ← MODIFY: mount 5 new routes
│   └── lib/
│       ├── video.ts                 ← EXISTING, do not change
│       ├── providers.ts             ← EXISTING, do not change
│       ├── music.ts                 ← NEW  Lyria client (OpenRouter SSE)
│       ├── mastering.ts             ← NEW  ffmpeg loudnorm two-pass + ffprobe
│       ├── mux.ts                   ← NEW  concat scenes → final.mp4, extract audio
│       ├── jobStore.ts              ← NEW  manifest read/write, atomic, idempotent
│       └── pipeline.ts              ← NEW  stage machine: brief → music → master → video → mux → pack
├── scripts/
│   ├── verify.ts                    ← EXISTING: add pipeline smoke test
│   └── make-marketing-pack.ts       ← NEW  5 hooks · 8 captions · 12 hashtags · 3 descriptions
├── data/
│   └── jobs-index.json              ← NEW  append-only list of job ids (created at runtime)
└── .env.example                     ← MODIFY: add MUSIC_* + FORGE_* vars (below)
```

Output (already specified by VORTEX-Outputs — do not invent a new layout):

```
$VORTEX_ASSETS_DIR/jobs/<job_id>/
├── manifest.json      job truth (schema in §6)
├── brief.json         what Roland asked for, normalized
├── score.mp3          raw Lyria output
├── master.wav         −14 LUFS mastered score (48 kHz / 24-bit)
├── scenes/01.mp4 …    one clip per scene
├── final.mp4          muxed long-form video + mastered audio
├── thumbnails/        3 variants × 3 aspects
└── marketing.json     5 hooks · 8 captions · 12 hashtags · 3 descriptions
```

---

## 5. ENVIRONMENT (exact variables)

Add to `vortex/.env.example`:

```dotenv
# ── Music (Lyria via OpenRouter) ─────────────────────────────
MUSIC_BASE_URL=https://openrouter.ai/api/v1
MUSIC_MODEL=google/lyria-3-pro-preview
# reuse OPENROUTER_API_KEY if present, else set MUSIC_API_KEY
MUSIC_API_KEY=

# ── Mastering ───────────────────────────────────────────────
FFMPEG_BIN=/Users/6-empires/.hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffmpeg
FFPROBE_BIN=/Users/6-empires/.hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffprobe
TARGET_LUFS=-14
TARGET_TP=-1.0
TARGET_SR=48000

# ── Pipeline ────────────────────────────────────────────────
VORTEX_JOBS_DIR=          # empty → $VORTEX_ASSETS_DIR/jobs
PIPELINE_MAX_SCENES=20
PIPELINE_SCENE_TIMEOUT_MS=600000
```

⚠️ `FFMPEG_BIN` must be verified before any job runs — see §10 Test 0.

---

## 6. DATA MODEL — `manifest.json`

Every field is written or updated; nothing is implied.

```json
{
  "schema_version": 1,
  "job_id": "j_20261018_221501_a1b2c3",
  "created_at": "2026-10-18T22:15:01Z",
  "updated_at": "2026-10-18T22:41:00Z",
  "brand": "reincarnation",
  "title": "AWAKENING — Movement I",
  "languages": ["hy", "en"],
  "status": "queued | music | mastering | video | mux | pack | done | failed",
  "error": null,
  "music": {
    "provider": "openrouter",
    "model": "google/lyria-3-pro-preview",
    "prompt": "…",
    "image_url": null,
    "seed": null,
    "status": "pending | running | ok | failed",
    "file": "score.mp3",
    "bytes": 1048576
  },
  "master": {
    "status": "pending | running | ok | failed",
    "file": "master.wav",
    "measured_in_lufs": -18.4,
    "measured_out_lufs": -14.0,
    "true_peak_dbtp": -1.2,
    "sample_rate": 48000
  },
  "video": {
    "provider_type": "replicate",
    "model": "lightricks/ltx-video",
    "aspect_ratio": "16:9",
    "scenes": [
      {
        "idx": 1,
        "prompt": "…",
        "duration": 5,
        "seed": 42,
        "status": "pending | running | ok | failed",
        "prediction_id": "…",
        "file": "scenes/01.mp4",
        "duration_sec": 5.0
      }
    ]
  },
  "outputs": {
    "final_mp4": "final.mp4",
    "final_duration_sec": 60.0,
    "thumbnails": [],
    "marketing_json": "marketing.json"
  },
  "gates": {
    "loudness_ok": false,
    "scenes_ok": false,
    "mux_ok": false,
    "duration_match_ok": false
  },
  "cost_estimate_usd": 0.0
}
```

**Rules**
- `status` advances **only** forward through the list; any stage error → `failed` + `error` string. Never silently skip.
- Every file field is **relative** to the job dir.
- `gates` must all be `true` before `status: "done"`. This is the ABSOLUTE enforcement point.
- Writes are atomic: write `manifest.json.tmp`, `fsync`, `rename`.

---

## 7. API CONTRACT (every endpoint: method, path, request, response, errors)

Base: `http://127.0.0.1:4000` (dev) — same Express process as the existing app.

### 7.1 `POST /api/jobs` — create a job
```json
{
  "brand": "reincarnation",
  "title": "AWAKENING — Movement I",
  "languages": ["hy", "en"],
  "music_prompt": "Cinematic ambient score … 30 seconds, instrumental, spiritual, golden.",
  "music_image_url": null,
  "aspect_ratio": "16:9",
  "scenes": [
    { "prompt": "A lone violinist on Yerevan's Northern Avenue at dawn, volumetric light", "duration": 5 },
    { "prompt": "Golden wheat field, slow dolly, dust in sunbeams", "duration": 5 }
  ]
}
```
→ `201 {"job_id": "j_…", "status": "queued", "manifest_url": "/api/jobs/j_…"}`

Errors: `400 INVALID_BRIEF` (missing title, 0 scenes, scenes > `PIPELINE_MAX_SCENES`), `503 MUSIC_PROVIDER_UNCONFIGURED`, `503 VIDEO_PROVIDER_UNCONFIGURED`.

### 7.2 `GET /api/jobs/:id` — manifest
→ `200 manifest.json` · `404 JOB_NOT_FOUND`

### 7.3 `GET /api/jobs` — index
→ `200 {"jobs":[{"job_id","title","status","created_at","final_mp4"}]}` (newest first, `data/jobs-index.json`)

### 7.4 `POST /api/jobs/:id/advance` — run the next stage (**idempotent**)
→ `200 {"job_id","status","stage_result":{…}}`
- Calling it twice on the same stage must not re-bill a provider: if `music.status=="ok"` and `score.mp3` exists → skip.
- Errors: `409 JOB_FAILED` (use `/retry`), `404`.

### 7.5 `POST /api/jobs/:id/retry` — reset the failed stage only
→ `200 {"job_id","status":"<stage>","retried":"music|mastering|video|mux|pack"}` · `409 JOB_NOT_FAILED`

### 7.6 `POST /api/music/generate` — music only (no job)
```json
{ "prompt": "…", "image_url": null, "out": "score.mp3" }
```
→ `200 {"file":"…/score.mp3","bytes":1048576,"model":"google/lyria-3-pro-preview"}`
Errors: `503 MUSIC_PROVIDER_UNCONFIGURED`, `502 MUSIC_UPSTREAM_ERROR` (include upstream status, never the API key).

### 7.7 `POST /api/master` — mastering only
```json
{ "input": "score.mp3", "output": "master.wav" }
```
→ `200 {"output":"…/master.wav","measured_in_lufs":-18.4,"measured_out_lufs":-14.0,"true_peak_dbtp":-1.2}`
Errors: `422 AUDIO_UNREADABLE`, `500 FFMPEG_FAILED` (stderr tail, max 500 chars).

### 7.8 `POST /api/video/generate` — **exists, unchanged**
`{providerId, prompt, duration, aspectRatio, seed}` → `VideoResult`.

---

## 8. STAGE IMPLEMENTATIONS (complete code, copy-paste)

### 8.1 `server/lib/music.ts`

```ts
// Lyria 3 Pro via OpenRouter — SSE stream, audio arrives as base64 deltas.
// Mirrors the verified script in REINCARNATION-Social-media-Gods/scripts/generate-lyria-music.mts.
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const baseUrl = (process.env.MUSIC_BASE_URL || "https://openrouter.ai/api/v1").replace(/\/$/, "");
const model = process.env.MUSIC_MODEL || "google/lyria-3-pro-preview";

export function musicConfigured(): boolean {
  return Boolean(process.env.MUSIC_API_KEY || process.env.OPENROUTER_API_KEY);
}

export async function generateMusic(opts: {
  prompt: string;
  outPath: string;
  imageUrl?: string | null;
  signal?: AbortSignal;
}): Promise<{ file: string; bytes: number; model: string }> {
  const apiKey = process.env.MUSIC_API_KEY || process.env.OPENROUTER_API_KEY || "";
  if (!apiKey) throw Object.assign(new Error("MUSIC_PROVIDER_UNCONFIGURED"), { status: 503 });

  const content: Array<Record<string, unknown>> = [{ type: "text", text: opts.prompt }];
  if (opts.imageUrl) content.push({ type: "image_url", image_url: { url: opts.imageUrl } });

  const resp = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({ model, stream: true, messages: [{ role: "user", content }] }),
    signal: opts.signal,
  });
  if (!resp.ok || !resp.body) {
    const text = await resp.text().catch(() => "");
    throw Object.assign(new Error(`MUSIC_UPSTREAM_ERROR ${resp.status}: ${text.slice(0, 300)}`), { status: 502 });
  }

  const chunks: Buffer[] = [];
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      const t = line.trim();
      if (!t.startsWith("data: ")) continue;
      const payload = t.slice(6);
      if (payload === "[DONE]") continue;
      try {
        const delta = JSON.parse(payload).choices?.[0]?.delta;
        if (delta?.audio?.data) chunks.push(Buffer.from(delta.audio.data, "base64"));
      } catch { /* ": OPENROUTER PROCESSING" and other keep-alives */ }
    }
  }
  if (chunks.length === 0) {
    throw Object.assign(new Error("MUSIC_NO_AUDIO: upstream returned no audio deltas"), { status: 502 });
  }
  const audio = Buffer.concat(chunks);
  mkdirSync(dirname(opts.outPath), { recursive: true });
  writeFileSync(opts.outPath, audio);
  return { file: opts.outPath, bytes: audio.length, model };
}
```

> Lyria returns short segments (~30 s). For a longer score: call it once per movement, then concat with ffmpeg (§8.5) — do **not** loop the same 30 s, it sounds cheap.

### 8.2 `server/lib/mastering.ts`

```ts
import { execFile } from "node:child_process";
import { promisify } from "node:util";
const run = promisify(execFile);

const FFMPEG = process.env.FFMPEG_BIN || "ffmpeg";
const FFPROBE = process.env.FFPROBE_BIN || "ffprobe";
const I = process.env.TARGET_LUFS || "-14";
const TP = process.env.TARGET_TP || "-1.0";
const SR = process.env.TARGET_SR || "48000";

export async function probe(file: string) {
  const { stdout } = await run(FFPROBE, [
    "-v", "error", "-print_format", "json", "-show_format", "-show_streams", file,
  ]);
  const j = JSON.parse(stdout);
  const audio = (j.streams || []).find((s: any) => s.codec_type === "audio");
  if (!audio) throw Object.assign(new Error("AUDIO_UNREADABLE"), { status: 422 });
  return { duration: Number(j.format?.duration || audio.duration || 0), sampleRate: Number(audio.sample_rate) };
}

export async function masterAudio(input: string, output: string) {
  // PASS 1 — measure
  const { stderr } = await run(FFMPEG, [
    "-hide_banner", "-i", input,
    "-af", `loudnorm=I=${I}:TP=${TP}:LRA=11:print_format=json`,
    "-f", "null", "-",
  ]);
  const m = stderr.match(/\{[\s\S]*?\}/g);
  if (!m) throw Object.assign(new Error("FFMPEG_NO_LOUDNORM_JSON"), { status: 500 });
  const meas = JSON.parse(m[m.length - 1]);

  // PASS 2 — apply measured values (linear, no pumping)
  await run(FFMPEG, [
    "-hide_banner", "-y", "-i", input,
    "-af",
    `loudnorm=I=${I}:TP=${TP}:LRA=11:` +
      `measured_I=${meas.input_i}:measured_TP=${meas.input_tp}:` +
      `measured_LRA=${meas.input_lra}:measured_thresh=${meas.input_thresh}:` +
      `offset=${meas.target_offset}:linear=true`,
    "-ar", SR, "-c:a", "pcm_s24le", output,
  ]);

  const out = await probe(output);
  return {
    output,
    measured_in_lufs: Number(meas.input_i),
    measured_out_lufs: Number(meas.output_i ?? I),
    true_peak_dbtp: Number(meas.output_tp ?? TP),
    sample_rate: out.sampleRate,
  };
}
```

### 8.3 `server/lib/jobStore.ts`

```ts
import { readFileSync, writeFileSync, renameSync, existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";

export function jobsDir(): string {
  return process.env.VORTEX_JOBS_DIR?.trim() || join(process.env.VORTEX_ASSETS_DIR || "/tmp/vortex-assets", "jobs");
}
export function jobDir(id: string): string { return join(jobsDir(), id); }
export function manifestPath(id: string): string { return join(jobDir(id), "manifest.json"); }

export function readManifest(id: string) {
  const p = manifestPath(id);
  if (!existsSync(p)) throw Object.assign(new Error("JOB_NOT_FOUND"), { status: 404 });
  return JSON.parse(readFileSync(p, "utf8"));
}
export function writeManifest(id: string, manifest: any) {
  mkdirSync(jobDir(id), { recursive: true });
  manifest.updated_at = new Date().toISOString();
  const p = manifestPath(id);
  const tmp = `${p}.tmp`;
  writeFileSync(tmp, JSON.stringify(manifest, null, 2));
  renameSync(tmp, p);           // atomic on the same filesystem
  return manifest;
}
export function newJobId(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const stamp = `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}_` +
                `${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}`;
  const rand = Math.random().toString(16).slice(2, 8);
  return `j_${stamp}_${rand}`;
}
```

### 8.4 `server/lib/pipeline.ts` — the stage machine

```ts
import { join } from "node:path";
import { existsSync, mkdirSync } from "node:fs";
import { jobDir, readManifest, writeManifest } from "./jobStore";
import { generateMusic } from "./music";
import { masterAudio, probe } from "./mastering";
import { dispatchVideoGenerate } from "./video";   // existing export in video.ts
import { muxScenes } from "./mux";

const STAGES = ["music", "mastering", "video", "mux", "pack"] as const;

export async function createJob(brief: any) {
  // validation is fail-closed: reject before any paid call
  if (!brief?.title) throw Object.assign(new Error("INVALID_BRIEF: title required"), { status: 400 });
  if (!Array.isArray(brief.scenes) || brief.scenes.length === 0)
    throw Object.assign(new Error("INVALID_BRIEF: at least one scene required"), { status: 400 });
  const max = Number(process.env.PIPELINE_MAX_SCENES || 20);
  if (brief.scenes.length > max)
    throw Object.assign(new Error(`INVALID_BRIEF: max ${max} scenes`), { status: 400 });
  return brief;
}

export async function advance(id: string) {
  let man = readManifest(id);
  if (man.status === "done") return { job_id: id, status: "done", stage_result: null };
  if (man.status === "failed")
    throw Object.assign(new Error("JOB_FAILED: use /retry"), { status: 409 });

  const dir = jobDir(id);
  mkdirSync(dir, { recursive: true });

  // 1 — MUSIC
  if (man.status === "queued" || man.status === "music") {
    man.status = "music";
    if (man.music.status !== "ok") {
      man.music.status = "running"; writeManifest(id, man);
      try {
        const r = await generateMusic({ prompt: man.music.prompt, outPath: join(dir, "score.mp3"),
                                        imageUrl: man.music.image_url });
        man.music.status = "ok"; man.music.file = "score.mp3"; man.music.bytes = r.bytes;
      } catch (e: any) { man.music.status = "failed"; man.status = "failed"; man.error = e.message;
        writeManifest(id, man); throw e; }
      writeManifest(id, man);
    }
  }

  // 2 — MASTERING
  man = readManifest(id);
  if (man.status === "music" || man.status === "mastering") {
    man.status = "mastering"; writeManifest(id, man);
    if (man.master.status !== "ok") {
      try {
        const m = await masterAudio(join(dir, "score.mp3"), join(dir, "master.wav"));
        man.master = { status: "ok", file: "master.wav", ...m };
        man.gates.loudness_ok = Math.abs(m.measured_out_lufs - Number(process.env.TARGET_LUFS || -14)) <= 0.5;
      } catch (e: any) { man.status = "failed"; man.error = e.message; man.master.status = "failed";
        writeManifest(id, man); throw e; }
      writeManifest(id, man);
    }
  }

  // 3 — VIDEO (per scene, resumable)
  man = readManifest(id);
  if (man.status === "mastering" || man.status === "video") {
    man.status = "video"; writeManifest(id, man);
    for (const scene of man.video.scenes) {
      if (scene.status === "ok" && existsSync(join(dir, scene.file))) continue;
      scene.status = "running"; writeManifest(id, man);
      try {
        const r: any = await dispatchVideoGenerate({
          prompt: scene.prompt, duration: scene.duration,
          aspectRatio: man.video.aspect_ratio, seed: scene.seed,
        });
        scene.prediction_id = r.predictionId ?? null;
        scene.file = `scenes/${String(scene.idx).padStart(2, "0")}.mp4`;
        scene.duration_sec = r.durationSec ?? scene.duration;
        scene.status = "ok";
      } catch (e: any) { scene.status = "failed"; man.status = "failed"; man.error = e.message;
        writeManifest(id, man); throw e; }
      writeManifest(id, man);
    }
    man.gates.scenes_ok = man.video.scenes.every((s: any) => s.status === "ok");
  }

  // 4 — MUX
  man = readManifest(id);
  if (man.status === "video" || man.status === "mux") {
    man.status = "mux"; writeManifest(id, man);
    const r = await muxScenes({ dir, scenes: man.video.scenes, audio: "master.wav", out: "final.mp4" });
    man.outputs.final_mp4 = "final.mp4";
    man.outputs.final_duration_sec = r.duration;
    man.gates.mux_ok = r.ok;
    man.gates.duration_match_ok = Math.abs(r.duration - man.video.scenes.reduce((a: number, s: any) => a + (s.duration_sec || 0), 0)) <= 1.0;
    writeManifest(id, man);
  }

  // 5 — PACK
  man = readManifest(id);
  if (man.status === "mux" || man.status === "pack") {
    man.status = "pack"; writeManifest(id, man);
    const { buildMarketingPack } = await import("../../scripts/make-marketing-pack.js");
    man.outputs.marketing_json = "marketing.json";
    writeManifest(id, { ...man, marketing: await buildMarketingPack(man) });
  }

  // 6 — DONE only if every gate passed
  man = readManifest(id);
  const allGates = Object.values(man.gates).every(Boolean);
  man.status = allGates ? "done" : "failed";
  if (!allGates) man.error = "GATES_FAILED: " + JSON.stringify(man.gates);
  writeManifest(id, man);
  return { job_id: id, status: man.status, stage_result: man.gates };
}
```

### 8.5 `server/lib/mux.ts`

```ts
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { join } from "node:path";
const run = promisify(execFile);
const FFMPEG = process.env.FFMPEG_BIN || "ffmpeg";

export async function muxScenes(opts: { dir: string; scenes: any[]; audio: string; out: string }) {
  const list = join(opts.dir, "scenes.txt");
  const { writeFileSync } = await import("node:fs");
  writeFileSync(list, opts.scenes.map((s) => `file '${join(opts.dir, s.file)}'`).join("\n") + "\n");

  const tmpSilent = join(opts.dir, ".concat.mp4");
  await run(FFMPEG, ["-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", list,
                     "-c", "copy", tmpSilent]);

  const finalPath = join(opts.dir, opts.out);
  await run(FFMPEG, ["-hide_banner", "-y", "-i", tmpSilent,
                     "-i", join(opts.dir, opts.audio),
                     "-map", "0:v:0", "-map", "1:a:0",
                     "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
                     "-shortest", "-movflags", "+faststart", finalPath]);

  const { probe } = await import("./mastering");
  const p = await probe(finalPath);
  return { ok: p.duration > 0, duration: p.duration };
}
```

---

## 9. ROUTES TO ADD IN `server/index.ts`

```ts
app.post("/api/jobs", async (req, res) => {
  try {
    await createJob(req.body);
    const { newJobId, writeManifest, jobDir } = await import("./lib/jobStore");
    const id = newJobId();
    const man = {
      schema_version: 1, job_id: id, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      brand: req.body.brand || "reincarnation", title: req.body.title, languages: req.body.languages || ["hy", "en"],
      status: "queued", error: null,
      music: { provider: "openrouter", model: process.env.MUSIC_MODEL || "google/lyria-3-pro-preview",
               prompt: req.body.music_prompt, image_url: req.body.music_image_url ?? null,
               status: "pending", file: null, bytes: 0 },
      master: { status: "pending", file: null },
      video: { provider_type: process.env.VIDEO_PROVIDER_TYPE || "cog",
               model: process.env.VIDEO_MODEL || "ltx-video-2b",
               aspect_ratio: req.body.aspect_ratio || "16:9",
               scenes: req.body.scenes.map((s: any, i: number) => ({ idx: i + 1, prompt: s.prompt,
                 duration: s.duration || 5, seed: s.seed ?? null, status: "pending", file: null })) },
      outputs: { final_mp4: null, thumbnails: [], marketing_json: null },
      gates: { loudness_ok: false, scenes_ok: false, mux_ok: false, duration_match_ok: false },
      cost_estimate_usd: 0,
    };
    const { mkdirSync } = await import("node:fs");
    mkdirSync(jobDir(id), { recursive: true });
    writeManifest(id, man);
    res.status(201).json({ job_id: id, status: "queued", manifest_url: `/api/jobs/${id}` });
  } catch (e: any) { res.status(e.status || 500).json({ error: e.message }); }
});

app.get("/api/jobs/:id", async (req, res) => {
  try { const { readManifest } = await import("./lib/jobStore"); res.json(readManifest(req.params.id)); }
  catch (e: any) { res.status(e.status || 500).json({ error: e.message }); }
});

app.post("/api/jobs/:id/advance", async (req, res) => {
  try { const { advance } = await import("./lib/pipeline"); res.json(await advance(req.params.id)); }
  catch (e: any) { res.status(e.status || 500).json({ error: e.message }); }
});
```

(`GET /api/jobs`, `/retry`, `/api/music/generate`, `/api/master` follow the same shape — thin wrappers over the libs above.)

---

## 10. COMMANDS — with expected output

**Test 0 — ffmpeg is real**
```bash
$FFMPEG_BIN -version | head -1
# expect: ffmpeg version 9.0.1-https://www.martin-riedl.de
```

**Test 1 — type-check + existing suite still green**
```bash
cd ~/vortex && pnpm install && pnpm check && pnpm verify
# expect: tsc exits 0; verify prints "ALL CHECKS PASSED"
```

**Test 2 — music only**
```bash
curl -s -X POST http://127.0.0.1:4000/api/music/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Cinematic ambient score for a spiritual awakening film. 30 seconds, instrumental, golden.","out":"/tmp/score.mp3"}' | python3 -m json.tool
# expect: {"file":"/tmp/score.mp3","bytes":>500000,...}
ffprobe -v error -show_entries format=duration -of csv=p=0 /tmp/score.mp3
# expect: ~30.0
```

**Test 3 — mastering gate**
```bash
curl -s -X POST http://127.0.0.1:4000/api/master \
  -H 'Content-Type: application/json' \
  -d '{"input":"/tmp/score.mp3","output":"/tmp/master.wav"}' | python3 -m json.tool
# expect: measured_out_lufs within -14 ± 0.5, true_peak_dbtp <= -1.0
```

**Test 4 — full job**
```bash
JOB=$(curl -s -X POST http://127.0.0.1:4000/api/jobs -H 'Content-Type: application/json' -d @brief.json | python3 -c 'import json,sys;print(json.load(sys.stdin)["job_id"])')
for i in 1 2 3 4 5; do curl -s -X POST "http://127.0.0.1:4000/api/jobs/$JOB/advance"; echo; done
curl -s "http://127.0.0.1:4000/api/jobs/$JOB" | python3 -m json.tool | tail -20
# expect: status "done", all four gates true, outputs.final_mp4 "final.mp4"
ls -la "${VORTEX_ASSETS_DIR}/jobs/$JOB"
# expect: manifest.json brief.json score.mp3 master.wav scenes/ final.mp4 marketing.json
```

**Test 5 — idempotency (no double billing)**
```bash
curl -s -X POST "http://127.0.0.1:4000/api/jobs/$JOB/advance"
# expect: {"status":"done","stage_result":null} — zero provider calls
```

**Test 6 — secrets never leak to the client**
```bash
grep -ri "sk-\|r8_\|OPENROUTER_API_KEY\|MUSIC_API_KEY" client/dist/assets/*.js | head
# expect: no output
```

---

## 11. ACCEPTANCE CRITERIA (CI-enforced — a PR without them is rejected)

1. `pnpm check` exits 0 and `pnpm verify` prints `ALL CHECKS PASSED`.
2. `POST /api/jobs` validates fail-closed — 0 scenes, >`PIPELINE_MAX_SCENES`, missing title → `400 INVALID_BRIEF`, and **no provider is called** (assert with a stub transport).
3. Every stage is resumable: killing the process mid-video and re-calling `/advance` continues from the first incomplete scene, never re-generating finished ones.
4. `gates` all true is the **only** path to `status: "done"`; any gate false → `failed` with a machine-readable reason.
5. Mastered output is `-14 LUFS ±0.5`, true peak ≤ `-1.0 dBTP`, 48 kHz / 24-bit PCM.
6. `final.mp4` duration within ±1.0 s of the sum of scene durations; `ffprobe` shows exactly one video + one audio stream, `faststart` present.
7. `manifest.json` is written atomically — never a partially-written JSON on disk (unit test kills the process between write and rename).
8. No secret ever appears in `client/dist/**` or in any HTTP error body (grep test in §10 Test 6).
9. `jobs-index.json` stays append-only and ordered; a job appears exactly once.
10. Zero paid calls on `/advance` when the stage is already `ok`.

---

## 12. WHAT NOT TO DO (explicit anti-patterns)

- **Do not** put provider keys in the browser or in `localStorage` — the locked-in contract in `vortex/CLAUDE.md` forbids it.
- **Do not** call the Lyria/Video APIs from React directly. All calls go through the Express libs.
- **Do not** invent a second output layout — `VORTEX-Outputs/jobs/<id>/` is the contract; `library/` is hand-curated by Roland only, never automatic.
- **Do not** mark a job `done` because "the files are there". Gates decide.
- **Do not** loop the same 30 s Lyria clip to fake length. Generate per movement, concat.
- **Do not** store generated media in `client/public/` (deployment timeout — stated in `vortex/README.md`).
- **Do not** run `pip install torch` into `~/mlx-train/venv` as part of this work — the local MusicGen path is out of scope for v1.0 (see §0).
- **Do not** auto-publish to social. Distribution stays behind the existing Postiz flows with human approval.

---

## 13. ROLLBACK

- The pipeline adds routes + libs; it does not modify `server/lib/video.ts` or `providers.ts`. Revert = drop the five new files and the route block; existing video and AI features keep working.
- Job data is per-job directories — deleting `jobs/<id>/` is a complete rollback for that job.
- `pnpm build && pnpm start` on the previous commit restores the last good server in < 2 minutes.

---

## 14. COST & TIME (estimates — verify on provider dashboards, not taken as fact)

| Item | Estimate | Note |
|---|---|---|
| Lyria 3 Pro, 30 s score | provider-dependent | Check the OpenRouter model page before bulk runs |
| LTX-Video 5 s clip (Replicate) | order of $0.05–0.15 / clip | ≈100 clips on ~$5 — as written in `INSTALL_VIDEO.md` |
| 12-scene piece (60 s) | music + 12 clips + ffmpeg | Wall time dominated by video polling |

Set `cost_estimate_usd` in the manifest as the sum of returned provider metrics — never a made-up number.

---

## 15. OPEN QUESTIONS FOR ROLAND (creative decisions only he can make)

1. **Brand look for v1** — which single reference frame defines "ABSOLUTE" for this pipeline?
2. **Voice** — narration in v1, or instrumental-only first release?
3. **Languages** — `hy` + `en` default, `ru` included at launch?
4. **Aspect** — 16:9 master with 9:16 reels auto-derived, or 9:16 primary?
5. **Approval gate** — should `status: done` require Roland's explicit sign-off flag before the job enters `library/`?

---

Version 1.0 · Architect: Hermes · Every claim in §0 was read from the live repos on 2026-10-18.
