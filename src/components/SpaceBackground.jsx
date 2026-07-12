import { useEffect, useRef } from "react"

// Vivid canvas-based crypto-space background:
// - 600+ stars in 4 parallax layers with colored twinkle
// - Pulsing multi-color nebulae
// - Aurora waves across top/bottom
// - Floating pixel planets/moons with rings
// - Drifting crypto glyphs (₿, Ξ, ◎, ◊, Ł, ◆, X, ¢)
// - Shooting stars + frequent comet trails
// - Animated constellation network
export default function SpaceBackground() {
  const ref = useRef(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    let w = 0, h = 0, raf = 0, t = 0

    const resize = () => {
      w = canvas.width = window.innerWidth * devicePixelRatio
      h = canvas.height = window.innerHeight * devicePixelRatio
      canvas.style.width  = window.innerWidth + "px"
      canvas.style.height = window.innerHeight + "px"
    }
    resize()
    window.addEventListener("resize", resize)

    // 4-layer starfield — varied colors
    const colors = ["#ffffff", "#00ffff", "#88ff00", "#ffff00", "#ff5577", "#cc44ff", "#00ddcc"]
    const mkStars = (n, speed, minR, maxR) =>
      Array.from({ length: n }, () => ({
        x: Math.random()*w, y: Math.random()*h,
        r: (minR + Math.random()*(maxR - minR)) * devicePixelRatio,
        s: speed * (0.4 + Math.random()*0.9),
        tw: Math.random() * Math.PI * 2,
        color: colors[Math.floor(Math.random() * colors.length)],
      }))
    const layers = [
      mkStars(260, 0.04, 0.4, 0.8),
      mkStars(180, 0.12, 0.6, 1.1),
      mkStars( 90, 0.24, 0.9, 1.8),
      mkStars( 30, 0.40, 1.2, 2.4),
    ]

    // Crypto glyphs — bigger, more colorful
    const glyphs = ["₿","Ξ","◎","Ł","◆","◊","⟠","X","¢","◉"]
    const tokens = Array.from({ length: 14 }, () => ({
      x: Math.random()*w, y: Math.random()*h,
      vx: (Math.random()-0.5)*0.25, vy: (Math.random()-0.5)*0.18,
      char: glyphs[Math.floor(Math.random()*glyphs.length)],
      size: (16 + Math.random()*22) * devicePixelRatio,
      opacity: 0.10 + Math.random()*0.15,
      hue: [120, 165, 190, 280, 330, 45][Math.floor(Math.random()*6)],
      pulsePhase: Math.random() * Math.PI * 2,
    }))

    // Constellation nodes
    const nodes = Array.from({ length: 24 }, () => ({
      x: Math.random()*w, y: Math.random()*h,
      vx: (Math.random()-0.5)*0.12, vy: (Math.random()-0.5)*0.12,
      r: 1.8 * devicePixelRatio,
      hue: [120, 180, 280, 55][Math.floor(Math.random()*4)],
    }))

    // Slowly drifting pixel planets
    const planets = [
      { x: 0.10, y: 0.18, r: 44, color: "#ff5577", ring: true,  ringColor: "#ffcc66", vx: 0.00012, vy: 0.00003 },
      { x: 0.85, y: 0.22, r: 30, color: "#00ddcc", ring: false,                         vx:-0.00008, vy: 0.00005 },
      { x: 0.20, y: 0.82, r: 36, color: "#88ff00", ring: true,  ringColor: "#00ffff", vx: 0.00006, vy:-0.00004 },
      { x: 0.80, y: 0.75, r: 24, color: "#cc44ff", ring: true,  ringColor: "#ff8800",  vx:-0.00010, vy:-0.00003 },
      { x: 0.50, y: 0.50, r: 18, color: "#ffff00", ring: false,                         vx: 0.00015, vy: 0.00002 },
      { x: 0.38, y: 0.10, r: 14, color: "#ff8800", ring: false,                         vx:-0.00014, vy: 0.00006 },
      { x: 0.65, y: 0.90, r: 20, color: "#00ffff", ring: false,                         vx: 0.00010, vy:-0.00005 },
    ]

    // Shooting stars
    let shooting = []
    const spawnShooting = () => {
      const hue = [120, 180, 60, 330][Math.floor(Math.random()*4)]
      shooting.push({
        x: Math.random()*w, y: Math.random()*h*0.6,
        vx: 8 + Math.random()*6, vy: 3 + Math.random()*3,
        life: 1, max: 80, hue,
      })
    }

    const drawPlanet = (p, time) => {
      // slow drift across viewport (wraps around)
      p.x = (p.x + p.vx + 1) % 1
      p.y = (p.y + p.vy + 1) % 1
      const cx = p.x * w
      const cy = p.y * h
      const r  = p.r * devicePixelRatio

      // strong glow halo
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 3.5)
      g.addColorStop(0, p.color + "aa")
      g.addColorStop(0.4, p.color + "44")
      g.addColorStop(1, p.color + "00")
      ctx.fillStyle = g
      ctx.fillRect(cx - r*3.5, cy - r*3.5, r*7, r*7)

      // body
      ctx.fillStyle = p.color
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.fill()

      // banded surface detail
      ctx.fillStyle = p.color
      ctx.globalAlpha = 0.6
      ctx.beginPath()
      ctx.arc(cx, cy + r * 0.3, r * 0.95, 0, Math.PI*2)
      ctx.fill()
      ctx.globalAlpha = 1

      // highlight crescent
      ctx.fillStyle = "rgba(255,255,255,0.32)"
      ctx.beginPath(); ctx.arc(cx - r*0.3, cy - r*0.3, r*0.5, 0, Math.PI*2); ctx.fill()

      // small shadow on opposite side
      ctx.fillStyle = "rgba(0,0,0,0.22)"
      ctx.beginPath(); ctx.arc(cx + r*0.35, cy + r*0.3, r*0.55, 0, Math.PI*2); ctx.fill()

      // ring (tilted)
      if (p.ring) {
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(time * 0.0008)
        ctx.strokeStyle = p.ringColor
        ctx.lineWidth = 2 * devicePixelRatio
        ctx.beginPath()
        ctx.ellipse(0, 0, r * 2.0, r * 0.55, 0, 0, Math.PI * 2)
        ctx.stroke()
        ctx.lineWidth = 0.8 * devicePixelRatio
        ctx.strokeStyle = p.ringColor + "aa"
        ctx.beginPath()
        ctx.ellipse(0, 0, r * 2.4, r * 0.68, 0, 0, Math.PI * 2)
        ctx.stroke()
        ctx.restore()
      }
    }

    const tick = () => {
      t += 1
      ctx.fillStyle = "#030714"
      ctx.fillRect(0, 0, w, h)

      // ── Deep cosmic nebulae — large, slow-drifting, rich colors ──
      const pulse = 0.75 + Math.sin(t * 0.008) * 0.25
      const driftX = (k) => Math.sin(t * 0.0008 + k) * 0.04
      const driftY = (k) => Math.cos(t * 0.0006 + k) * 0.03
      const nebulae = [
        { x: 0.20, y: 0.25, r: 0.70, col: "rgba(0,255,150,"   },
        { x: 0.78, y: 0.30, r: 0.65, col: "rgba(200,100,255," },
        { x: 0.50, y: 0.55, r: 0.60, col: "rgba(0,180,255,"   },
        { x: 0.30, y: 0.75, r: 0.55, col: "rgba(255,120,200," },
        { x: 0.82, y: 0.80, r: 0.58, col: "rgba(255,180,60,"  },
        { x: 0.15, y: 0.55, r: 0.50, col: "rgba(136,255,50,"  },
      ]
      for (let i = 0; i < nebulae.length; i++) {
        const n = nebulae[i]
        const cx = (n.x + driftX(i)) * w
        const cy = (n.y + driftY(i)) * h
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(w, h) * n.r)
        g.addColorStop(0,    n.col + (0.40 * pulse) + ")")
        g.addColorStop(0.25, n.col + (0.20 * pulse) + ")")
        g.addColorStop(0.55, n.col + (0.08 * pulse) + ")")
        g.addColorStop(1,    n.col + "0)")
        ctx.fillStyle = g
        ctx.fillRect(0, 0, w, h)
      }

      // (aurora waves + neon scan beams removed — pure deep space)

      // ── Distant galaxy swirls (soft colored disc glows) ──
      const galaxies = [
        { x: 0.08, y: 0.30, r: 120, hue: 280, rot: t * 0.0015 },
        { x: 0.92, y: 0.25, r: 160, hue: 180, rot: -t * 0.0012 },
        { x: 0.45, y: 0.05, r: 100, hue: 330, rot: t * 0.002  },
        { x: 0.75, y: 0.70, r: 140, hue: 45,  rot: -t * 0.001 },
      ]
      for (const g of galaxies) {
        ctx.save()
        ctx.translate(g.x * w, g.y * h)
        ctx.rotate(g.rot)
        const grad = ctx.createRadialGradient(0, 0, 0, 0, 0, g.r * devicePixelRatio)
        grad.addColorStop(0,   `hsla(${g.hue}, 90%, 70%, 0.28)`)
        grad.addColorStop(0.3, `hsla(${g.hue}, 90%, 60%, 0.14)`)
        grad.addColorStop(1,   `hsla(${g.hue}, 90%, 50%, 0)`)
        ctx.fillStyle = grad
        // Elliptical galaxy shape
        ctx.beginPath()
        ctx.ellipse(0, 0, g.r * devicePixelRatio, g.r * 0.4 * devicePixelRatio, 0, 0, Math.PI*2)
        ctx.fill()
        ctx.restore()
      }

      // ── Stars with color twinkle ──
      for (const layer of layers) {
        for (const s of layer) {
          s.x -= s.s * devicePixelRatio
          if (s.x < -4) s.x = w + 4
          s.tw += 0.035
          const tw = 0.55 + 0.45 * Math.sin(s.tw)
          ctx.fillStyle = s.color
          ctx.globalAlpha = 0.4 + tw * 0.55
          ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI*2); ctx.fill()
          // cross spike for biggest stars
          if (s.r > 1.2 * devicePixelRatio) {
            ctx.globalAlpha = 0.3 + tw * 0.4
            ctx.fillRect(s.x - s.r*2, s.y - 0.3, s.r*4, 0.6)
            ctx.fillRect(s.x - 0.3, s.y - s.r*2, 0.6, s.r*4)
          }
        }
      }
      ctx.globalAlpha = 1

      // ── Constellation network ──
      for (const n of nodes) {
        n.x += n.vx; n.y += n.vy
        if (n.x < 0 || n.x > w) n.vx *= -1
        if (n.y < 0 || n.y > h) n.vy *= -1
      }
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i+1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j]
          const dx = a.x - b.x, dy = a.y - b.y
          const dist = Math.hypot(dx, dy)
          const maxD = 240 * devicePixelRatio
          if (dist < maxD) {
            const alpha = (1 - dist/maxD) * 0.22
            ctx.strokeStyle = `hsla(${a.hue}, 80%, 60%, ${alpha})`
            ctx.lineWidth = 0.8 * devicePixelRatio
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke()
          }
        }
        const n = nodes[i]
        ctx.fillStyle = `hsla(${n.hue}, 80%, 65%, 0.85)`
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI*2); ctx.fill()
      }

      // ── Planets with rings ──
      for (const p of planets) drawPlanet(p, t)

      // ── Crypto glyphs (pulsing) ──
      for (const tk of tokens) {
        tk.x += tk.vx; tk.y += tk.vy
        if (tk.x < -40) tk.x = w + 40
        if (tk.x > w + 40) tk.x = -40
        if (tk.y < -40) tk.y = h + 40
        if (tk.y > h + 40) tk.y = -40
        const pulseO = tk.opacity + Math.sin(t * 0.02 + tk.pulsePhase) * 0.05
        ctx.font = `bold ${tk.size}px 'Press Start 2P', monospace`
        ctx.fillStyle = `hsla(${tk.hue}, 85%, 65%, ${Math.max(0.05, pulseO)})`
        ctx.shadowColor = `hsl(${tk.hue}, 85%, 55%)`
        ctx.shadowBlur = 8 * devicePixelRatio
        ctx.fillText(tk.char, tk.x, tk.y)
      }
      ctx.shadowBlur = 0

      // ── Shooting stars (frequent) ──
      if (Math.random() < 0.015) spawnShooting()
      shooting = shooting.filter(s => {
        s.x += s.vx * devicePixelRatio
        s.y += s.vy * devicePixelRatio
        s.life -= 1/s.max
        if (s.life <= 0) return false
        const g = ctx.createLinearGradient(s.x, s.y, s.x - 60, s.y - 22)
        g.addColorStop(0, `hsla(${s.hue}, 90%, 70%, ${s.life})`)
        g.addColorStop(0.5, `hsla(${s.hue}, 90%, 60%, ${s.life*0.5})`)
        g.addColorStop(1, "rgba(255,255,255,0)")
        ctx.strokeStyle = g
        ctx.lineWidth = 2 * devicePixelRatio
        ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(s.x - 60, s.y - 22); ctx.stroke()
        // sparkle
        ctx.fillStyle = `hsla(${s.hue}, 90%, 85%, ${s.life})`
        ctx.beginPath(); ctx.arc(s.x, s.y, 1.5*devicePixelRatio, 0, Math.PI*2); ctx.fill()
        return true
      })

      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize) }
  }, [])

  return (
    <canvas
      ref={ref}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
    />
  )
}
