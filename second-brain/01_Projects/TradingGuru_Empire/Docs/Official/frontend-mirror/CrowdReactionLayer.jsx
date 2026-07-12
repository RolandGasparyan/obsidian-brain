/**
 * CrowdReactionLayer — particle burst reactions to REAL terminal.json deltas.
 *
 * Subscribes to useTerminalDeltas. Each event type triggers a distinct
 * particle pattern (color, count, motion, lifespan). Particles are pooled
 * (recycled) — no GC churn on repeated bursts. Hard cap 150 active particles.
 *
 * Phase 2 · 2026-05-12 · Feature G
 *
 * Key principle (per Phase 1 architecture):
 *   Every burst is triggered by a REAL backend delta. Math.random is used
 *   ONLY for visual scatter within a burst (direction/speed jitter), never
 *   for triggering or for content selection.
 */
import { useEffect, useRef } from "react"
import { useTerminalDeltas, EVENT_TYPE } from "../../lib/useTerminalDeltas.js"
import { usePaperArena } from "../../lib/usePaperArena.js"

const MAX_PARTICLES = 150

// ── Phase 10: paper-event particle recipes ────────────────────────────────
// Paper events from /api/battle/paper-arena.json fire smaller, gentler bursts
// (clearly less intense than real Layer 2 events — paper mode should feel
// alive but not equally weighted as real backend signals).
const PAPER_BURST_CONFIG = {
  WIN_STREAK: {
    count: 30, color: [50, 220, 100], speed: 5, life: 80, gravity: -0.04, shape: "confetti",
  },
  LOSS_STREAK: {
    count: 25, color: [220, 80, 80], speed: 4, life: 70, gravity: 0.08, shape: "shrapnel",
  },
  BIG_SIM_SWING: {
    count: 35, color: [255, 200, 60], speed: 6, life: 90, gravity: -0.03, shape: "spark",
  },
  STATUS_CHANGE: {
    count: 15, color: [0, 220, 240], speed: 3, life: 60, gravity: 0, shape: "ring",
  },
}

// Color override for BIG_SIM_SWING based on pnl sign
function paperColorForEvent(event) {
  if (event.type === "BIG_SIM_SWING" && typeof event.pnl_sim_usd === "number") {
    return event.pnl_sim_usd > 0 ? [50, 220, 100] : [220, 80, 80]
  }
  return null
}

// Per-event burst recipe
const BURST_CONFIG = {
  [EVENT_TYPE.BTC_BREAKOUT_UP]: {
    count: 60, color: [50, 255, 100], speed: 7, life: 110, gravity: -0.04, shape: "confetti",
  },
  [EVENT_TYPE.BTC_BREAKOUT_DOWN]: {
    count: 50, color: [255, 80, 100], speed: 6, life: 100, gravity: 0.12, shape: "shrapnel",
  },
  [EVENT_TYPE.GOD_CANDLE]: {
    count: 90, color: [255, 215, 0],  speed: 9, life: 130, gravity: -0.02, shape: "spark",
  },
  [EVENT_TYPE.KILLSWITCH_FIRE]: {
    count: 80, color: [255, 50, 70],  speed: 8, life: 120, gravity: 0.08,  shape: "shrapnel",
  },
  [EVENT_TYPE.KILLSWITCH_NEAR]: {
    count: 30, color: [255, 170, 50], speed: 4, life: 80,  gravity: 0,     shape: "ring",
  },
  [EVENT_TYPE.HALT_TRIGGERED]: {
    count: 100, color: [255, 30, 60], speed: 10, life: 140, gravity: 0,    shape: "ring",
  },
  [EVENT_TYPE.EQUITY_NEW_HIGH]: {
    count: 40, color: [255, 215, 80], speed: 5, life: 90,  gravity: -0.06, shape: "spark",
  },
  [EVENT_TYPE.EQUITY_DD]: {
    count: 35, color: [255, 100, 80], speed: 3.5, life: 80, gravity: 0.05, shape: "shrapnel",
  },
  [EVENT_TYPE.SAFE_MODE_ON]: {
    count: 50, color: [255, 200, 60], speed: 4, life: 90,  gravity: 0,     shape: "ring",
  },
  [EVENT_TYPE.SAFE_MODE_OFF]: {
    count: 40, color: [50, 255, 100], speed: 4, life: 90,  gravity: 0,     shape: "ring",
  },
  [EVENT_TYPE.VOLATILITY_SPIKE]: {
    count: 70, color: [255, 230, 80], speed: 6, life: 100, gravity: 0,     shape: "wave",
  },
  [EVENT_TYPE.AGENT_LEAD_CHANGE]: {
    count: 25, color: [0, 240, 255],  speed: 4, life: 70,  gravity: -0.03, shape: "spark",
  },
  [EVENT_TYPE.HALT_LIFTED]: {
    count: 60, color: [50, 255, 100], speed: 5, life: 100, gravity: -0.04, shape: "confetti",
  },
  [EVENT_TYPE.BOT_RESTART]: {
    count: 30, color: [0, 240, 255],  speed: 3, life: 80,  gravity: 0,     shape: "ring",
  },
}

export default function CrowdReactionLayer({ opacity = 0.85, zIndex = 35 }) {
  const canvasRef = useRef(null)
  const events = useTerminalDeltas()
  const { data: paperData, isPaperMode } = usePaperArena()
  const seenRef = useRef(new Set())
  const particlesRef = useRef([])
  const queueRef = useRef([])

  // Detect new REAL events → enqueue burst
  useEffect(() => {
    for (const e of events) {
      if (seenRef.current.has(e.id)) continue
      seenRef.current.add(e.id)
      const cfg = BURST_CONFIG[e.type]
      if (cfg) queueRef.current.push({ event: e, cfg })
    }
  }, [events])

  // Phase 10: Detect new PAPER events → enqueue smaller burst.
  // Each paper event has type + agent_id + cycle → derive a unique id.
  useEffect(() => {
    if (!isPaperMode || !paperData?.events) return
    for (const e of paperData.events) {
      const evId = `paper:${e.type}:${e.agent_id}:${e.cycle}`
      if (seenRef.current.has(evId)) continue
      seenRef.current.add(evId)
      let cfg = PAPER_BURST_CONFIG[e.type]
      if (!cfg) continue
      // Override color for BIG_SIM_SWING based on pnl sign
      const colorOverride = paperColorForEvent(e)
      if (colorOverride) cfg = { ...cfg, color: colorOverride }
      queueRef.current.push({ event: { ...e, id: evId }, cfg })
    }
  }, [paperData, isPaperMode])

  // Single render loop with pooled particles
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    let raf

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener("resize", resize)

    const spawnBurst = (cfg) => {
      const cx = canvas.width / 2
      const cy = canvas.height / 2
      for (let i = 0; i < cfg.count; i++) {
        if (particlesRef.current.length >= MAX_PARTICLES) break
        let vx, vy
        switch (cfg.shape) {
          case "confetti": {
            const a = Math.random() * Math.PI - Math.PI / 2  // upward fan
            vx = Math.cos(a) * (cfg.speed * (0.6 + Math.random() * 0.8))
            vy = Math.sin(a) * (cfg.speed * (0.6 + Math.random() * 0.8))
            break
          }
          case "shrapnel": {
            const a = Math.random() * Math.PI * 2
            vx = Math.cos(a) * (cfg.speed * (0.5 + Math.random() * 1.2))
            vy = Math.sin(a) * (cfg.speed * (0.5 + Math.random() * 1.2))
            break
          }
          case "ring": {
            const a = (i / cfg.count) * Math.PI * 2
            vx = Math.cos(a) * cfg.speed
            vy = Math.sin(a) * cfg.speed
            break
          }
          case "wave": {
            const a = (i / cfg.count) * Math.PI * 2
            vx = Math.cos(a) * cfg.speed * 1.2
            vy = Math.sin(a) * cfg.speed * 0.4
            break
          }
          case "spark":
          default: {
            const a = Math.random() * Math.PI * 2
            const sp = cfg.speed * (0.6 + Math.random() * 0.8)
            vx = Math.cos(a) * sp
            vy = Math.sin(a) * sp
          }
        }
        particlesRef.current.push({
          x: cx, y: cy, vx, vy,
          life: cfg.life, maxLife: cfg.life,
          color: cfg.color, shape: cfg.shape,
          gravity: cfg.gravity,
          size: cfg.shape === "ring" ? 2 : (1.5 + Math.random() * 1.5),
        })
      }
    }

    const tick = () => {
      // Drain burst queue (one per frame to spread cost)
      if (queueRef.current.length > 0) {
        const { cfg } = queueRef.current.shift()
        spawnBurst(cfg)
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const surviving = []
      for (const p of particlesRef.current) {
        p.x += p.vx
        p.y += p.vy
        p.vy += p.gravity
        p.life--
        if (p.life <= 0) continue
        const t = p.life / p.maxLife
        const alpha = Math.max(0, Math.min(1, t)) * 0.95
        ctx.fillStyle = `rgba(${p.color[0]},${p.color[1]},${p.color[2]},${alpha.toFixed(3)})`
        if (p.shape === "ring" || p.shape === "wave") {
          // Larger glowing dot
          ctx.fillRect(p.x - p.size, p.y - p.size, p.size * 2, p.size * 2)
        } else if (p.shape === "shrapnel") {
          ctx.fillRect(p.x, p.y, 2.5, 2.5)
        } else {
          ctx.beginPath()
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
          ctx.fill()
        }
        surviving.push(p)
      }
      particlesRef.current = surviving

      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener("resize", resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex, opacity, mixBlendMode: "screen" }}
      aria-hidden
    />
  )
}
