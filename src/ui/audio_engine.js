// Lightweight Web Audio SFX — no asset files. All tones are synthesized.
// Volumes intentionally low; designed to be subtle, not arcade-y.

let ctx = null
let masterGain = null       // controlled by per-track automation (party music, etc.)
let muteGain = null         // ONLY controlled by setEnabled — hard on/off
let enabled = true
// Track scheduled sound stop times so we can kill everything on mute
let activeSources = []

// ── Sample-based SFX (MP3s) ─────────────────────────────────────
const SAMPLES = {
  ufoLanding: { url: "/audio/ufo-landing.mp3", volume: 0.6,  loop: false },
  partyLoop:  { url: "/audio/party-loop.mp3",  volume: 0.42, loop: true  },
}
const samplePool = {}    // key → HTMLAudioElement (lazy)

function getSample(key) {
  if (samplePool[key]) return samplePool[key]
  const spec = SAMPLES[key]
  if (!spec) return null
  const a = new Audio(spec.url)
  a.preload = "auto"
  a.volume  = spec.volume
  a.loop    = spec.loop
  samplePool[key] = a
  return a
}

function playSample(key) {
  if (!enabled) return null
  const a = getSample(key)
  if (!a) return null
  try {
    a.currentTime = 0
    const p = a.play()
    if (p && p.catch) p.catch(() => {})
  } catch {}
  return a
}

// Play a sample so that its END coincides with `msFromNow` (ms).
// Usage: aligns the final impact moment of a landing sound with the visual touchdown.
function playSampleToFinishAt(key, msFromNow, tailOffsetMs = 250) {
  if (!enabled) return
  const a = getSample(key)
  if (!a) return

  const schedule = () => {
    const dur = (a.duration || 0) * 1000
    if (!dur) {
      // metadata not ready — play immediately as fallback
      playSample(key)
      return
    }
    const startIn = Math.max(0, msFromNow - dur + tailOffsetMs)
    setTimeout(() => playSample(key), startIn)
  }

  if (a.readyState >= 1 && a.duration) {
    schedule()
  } else {
    a.addEventListener("loadedmetadata", schedule, { once: true })
    // Nudge the browser to load
    try { a.load() } catch {}
  }
}

function stopSample(key) {
  const a = samplePool[key]
  if (!a) return
  try { a.pause(); a.currentTime = 0 } catch {}
}

function stopAllSamples() {
  for (const key of Object.keys(samplePool)) stopSample(key)
}

function ensure() {
  if (ctx) return ctx
  try {
    const AC = window.AudioContext || window.webkitAudioContext
    ctx = new AC()
    masterGain = ctx.createGain()
    masterGain.gain.value = 0.18 // soft

    muteGain = ctx.createGain()
    muteGain.gain.value = 1     // default: audible

    masterGain.connect(muteGain)
    muteGain.connect(ctx.destination)
  } catch { ctx = null }
  return ctx
}

function registerSource(node) {
  activeSources.push(node)
  // auto-remove when it ends
  try { node.addEventListener?.("ended", () => {
    activeSources = activeSources.filter(n => n !== node)
  }) } catch {}
}

export function setEnabled(v) {
  enabled = !!v
  const c = ensure()
  if (c && muteGain) {
    muteGain.gain.cancelScheduledValues(c.currentTime)
    muteGain.gain.setValueAtTime(enabled ? 1 : 0, c.currentTime)
    if (!enabled) {
      for (const node of activeSources) { try { node.stop?.(c.currentTime) } catch {} }
      activeSources = []
    }
  }
  // Also stop MP3 samples
  if (!enabled) stopAllSamples()
  // Sync sample volumes with enabled state
  for (const key of Object.keys(samplePool)) {
    try { samplePool[key].muted = !enabled } catch {}
  }
}
export function isEnabled()   { return enabled }

function blip({ freq = 440, dur = 0.08, type = "sine", vol = 0.25, attack = 0.005, decay = 0.08 }) {
  if (!enabled) return
  const c = ensure(); if (!c) return
  if (c.state === "suspended") c.resume().catch(()=>{})
  const o = c.createOscillator()
  const g = c.createGain()
  o.type = type
  o.frequency.value = freq
  const now = c.currentTime
  g.gain.setValueAtTime(0, now)
  g.gain.linearRampToValueAtTime(vol, now + attack)
  g.gain.exponentialRampToValueAtTime(0.0001, now + attack + decay)
  o.connect(g); g.connect(masterGain)
  o.start(now); o.stop(now + attack + decay + 0.02)
  registerSource(o)
}

function swell({ from = 220, to = 660, dur = 0.6, vol = 0.35 }) {
  if (!enabled) return
  const c = ensure(); if (!c) return
  if (c.state === "suspended") c.resume().catch(()=>{})
  const o = c.createOscillator()
  const g = c.createGain()
  o.type = "sine"
  const now = c.currentTime
  o.frequency.setValueAtTime(from, now)
  o.frequency.exponentialRampToValueAtTime(to, now + dur)
  g.gain.setValueAtTime(0, now)
  g.gain.linearRampToValueAtTime(vol, now + 0.08)
  g.gain.exponentialRampToValueAtTime(0.0001, now + dur)
  o.connect(g); g.connect(masterGain)
  o.start(now); o.stop(now + dur + 0.05)
  registerSource(o)
}

// Throttle hover sound so it doesn't spam
let lastHover = 0
export const audio = {
  click:      () => blip({ freq: 880, dur: 0.05, type: "triangle", vol: 0.12 }),
  hover:      () => {
    const now = performance.now()
    if (now - lastHover < 140) return
    lastHover = now
    blip({ freq: 1200, dur: 0.035, type: "sine", vol: 0.05 })
  },
  entry:      () => blip({ freq: 523, dur: 0.10, type: "sine",     vol: 0.18 }),
  exit:       () => blip({ freq: 349, dur: 0.12, type: "sine",     vol: 0.18 }),
  win:        () => blip({ freq: 659, dur: 0.16, type: "sine",     vol: 0.20 }),
  loss:       () => blip({ freq: 196, dur: 0.14, type: "triangle", vol: 0.18 }),
  bigWin:     () => { swell({ from: 220, to: 660, dur: 0.6, vol: 0.28 })
                      setTimeout(()=>blip({ freq: 90, dur: 0.20, type: "sine", vol: 0.22 }), 30) },
  warning:    () => blip({ freq: 140, dur: 0.35, type: "sawtooth", vol: 0.12, decay: 0.35 }),
  intro:      () => swell({ from: 110, to: 330, dur: 0.9, vol: 0.22 }),
  // Arcade pings for arena
  ping:       () => blip({ freq: 1760, dur: 0.04, type: "sine", vol: 0.07 }),
  speak:      () => blip({ freq: 440,  dur: 0.08, type: "triangle", vol: 0.10 }),
  // Coin drop — rapid descending triangle blips (like Mario coins cascading)
  coinDrop:   () => {
    const notes = [1320, 1760, 1480, 2000, 1600, 2200, 1700, 2400]
    notes.forEach((f, i) => {
      setTimeout(() => blip({ freq: f, dur: 0.07, type: "triangle", vol: 0.13, decay: 0.07 }), i * 70)
    })
  },
  // UFO arrival whoosh — descending then rising swell
  ufoArrive:  () => {
    swell({ from: 880, to: 220, dur: 0.7, vol: 0.22 })
    setTimeout(() => swell({ from: 220, to: 660, dur: 0.5, vol: 0.18 }), 700)
  },
  // Text reveal whoosh — high-to-mid sweep + shimmer
  textReveal: () => {
    swell({ from: 2400, to: 800, dur: 0.5, vol: 0.14 })
    setTimeout(() => blip({ freq: 1760, dur: 0.1, type: "sine", vol: 0.10 }), 150)
  },
  // UFO descent drone — long low-mid sweep
  ufoDescent: () => {
    swell({ from: 220, to: 80, dur: 1.8, vol: 0.20 })
    setTimeout(() => blip({ freq: 140, dur: 0.3, type: "triangle", vol: 0.12, decay: 0.3 }), 1700)
  },
  // Beam activation — rising shimmer + sustained tone
  beamOn: () => {
    swell({ from: 440, to: 1320, dur: 0.9, vol: 0.18 })
    setTimeout(() => blip({ freq: 880, dur: 0.5, type: "sine", vol: 0.12, decay: 0.5 }), 400)
    setTimeout(() => blip({ freq: 1320, dur: 0.4, type: "triangle", vol: 0.08, decay: 0.4 }), 600)
  },
  // UFO landing — real MP3 sample (fire immediately at touchdown)
  ufoLanding: () => { playSample("ufoLanding") },
  // UFO landing synced — schedule so the sound's tail coincides with `msFromNow` touchdown
  ufoLandingSync: (msFromNow, tailOffsetMs) =>
    playSampleToFinishAt("ufoLanding", msFromNow, tailOffsetMs),
  // Preload MP3s so duration is known before we need to sync
  preloadSamples: () => {
    getSample("ufoLanding")?.load()
    getSample("partyLoop")?.load()
  },
  // Final chord — triumphant major triad
  triumph: () => {
    blip({ freq: 523, dur: 1.2, type: "sine", vol: 0.16, decay: 1.2 })    // C5
    setTimeout(() => blip({ freq: 659, dur: 1.1, type: "sine", vol: 0.14, decay: 1.1 }), 40) // E5
    setTimeout(() => blip({ freq: 784, dur: 1.0, type: "sine", vol: 0.12, decay: 1.0 }), 80) // G5
  },
  // Party music — real Daft Punk MP3 loop (stops automatically after ~4s dance window)
  partyMusic: () => {
    const a = playSample("partyLoop")
    // Auto-stop after dance mode ends (4s)
    setTimeout(() => stopSample("partyLoop"), 4000)
  },
  // Manual stop (used when sound toggled off mid-dance)
  partyMusicStop: () => stopSample("partyLoop"),
}

// Some browsers require a user gesture. Attach a one-shot unlock.
if (typeof window !== "undefined") {
  const unlock = () => {
    ensure()
    if (ctx && ctx.state === "suspended") ctx.resume().catch(()=>{})
    window.removeEventListener("pointerdown", unlock)
    window.removeEventListener("keydown", unlock)
  }
  window.addEventListener("pointerdown", unlock, { once: true })
  window.addEventListener("keydown",     unlock, { once: true })
}
