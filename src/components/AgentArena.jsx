import { useEffect, useMemo, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { AGENTS } from "./AgentSprites.jsx"
import { audio } from "../ui/audio_engine.js"

// Each agent has a "work zone" — 3 waypoints spread across the WHOLE arena.
// Top row (desks near wall) + bottom row (standing zone).
const ZONES = {
  alpha:    [[10, 24], [18, 20], [14, 30]],   // top-left
  skeptic:  [[30, 22], [36, 28], [26, 18]],   // upper-left-center
  executor: [[52, 26], [58, 32], [48, 22]],   // upper-center
  regime:   [[72, 22], [78, 28], [68, 32]],   // upper-right-center
  risk:     [[90, 26], [86, 32], [94, 22]],   // top-right
  hunter:   [[18, 72], [24, 78], [14, 66]],   // lower-left
  champion: [[48, 78], [54, 72], [42, 72]],   // lower-center
  recovery: [[82, 72], [88, 66], [76, 78]],   // lower-right
}

const LINES = [
  ["alpha", "executor"], ["alpha", "skeptic"], ["skeptic", "executor"],
  ["executor", "regime"], ["executor", "risk"], ["executor", "recovery"],
  ["regime", "hunter"],   ["risk", "champion"], ["hunter", "champion"],
  ["recovery", "risk"],   ["alpha", "regime"],
]

const STATUSES = ["SCAN", "VOTE", "HEDGE", "EXEC", "CALC", "POLL", "RANK", "PING", "FEED", "WAIT", "READY", "SYNC"]

// Agent activity emotes
const ACTIVITIES = ["work", "coffee", "bread", "smoke", "sleep", "phone", "music"]
function ActivityEmote({ kind }) {
  if (!kind || kind === "work") return null
  const base = "absolute -top-6 left-1/2 -translate-x-1/2 pointer-events-none"
  const px = 3
  switch (kind) {
    case "coffee":
      return (
        <div className={base}>
          <svg width={18} height={22} viewBox="0 0 6 8" style={{ imageRendering: "pixelated" }}>
            {/* steam */}
            <motion.g animate={{ y: [0, -1, 0] }} transition={{ duration: 0.8, repeat: Infinity }}>
              <rect x="2" y="0" width="0.5" height="1" fill="#c0ddf0" opacity="0.5" />
              <rect x="3.5" y="0.5" width="0.5" height="1" fill="#c0ddf0" opacity="0.5" />
            </motion.g>
            {/* mug */}
            <rect x="1" y="3" width="4" height="1" fill="#c0ddf0" />
            <rect x="1" y="4" width="4" height="3" fill="#c0ddf0" />
            <rect x="5" y="4.5" width="0.5" height="1.5" fill="#c0ddf0" />
            <rect x="1.5" y="4" width="3" height="0.7" fill="#6b4020" />
          </svg>
        </div>
      )
    case "bread":
      return (
        <div className={base}>
          <svg width={20} height={16} viewBox="0 0 7 5" style={{ imageRendering: "pixelated" }}>
            <rect x="0" y="2" width="7" height="2" fill="#ffaa44" />
            <rect x="0" y="1" width="7" height="1" fill="#ffcc66" />
            <rect x="1" y="2" width="5" height="1" fill="#88ff00" />
            <rect x="1" y="3" width="5" height="1" fill="#ff5577" />
          </svg>
        </div>
      )
    case "smoke":
      return (
        <div className={base}>
          <svg width={18} height={22} viewBox="0 0 6 8" style={{ imageRendering: "pixelated" }}>
            <motion.g animate={{ y: [0, -2, -4, 0], opacity: [1, 0.7, 0, 1] }} transition={{ duration: 1.4, repeat: Infinity, ease: "easeOut" }}>
              <rect x="2.5" y="0" width="0.8" height="0.8" fill="#c0ddf0" opacity="0.6" />
              <rect x="3" y="1.5" width="0.6" height="0.6" fill="#c0ddf0" opacity="0.5" />
            </motion.g>
            {/* cigarette */}
            <rect x="1" y="4" width="3.5" height="0.8" fill="#c0ddf0" />
            <rect x="4.5" y="4" width="0.5" height="0.8" fill="#ff5500" />
          </svg>
        </div>
      )
    case "sleep":
      return (
        <motion.div
          className={base}
          animate={{ y: [0, -2, 0], opacity: [1, 0.6, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          <svg width={18} height={18} viewBox="0 0 6 6" style={{ imageRendering: "pixelated" }}>
            <rect x="1" y="0" width="4" height="1" fill="#00ffff" />
            <rect x="4" y="1" width="1" height="1" fill="#00ffff" />
            <rect x="3" y="2" width="1" height="1" fill="#00ffff" />
            <rect x="2" y="3" width="1" height="1" fill="#00ffff" />
            <rect x="1" y="4" width="4" height="1" fill="#00ffff" />
          </svg>
        </motion.div>
      )
    case "phone":
      return (
        <div className={base}>
          <svg width={16} height={18} viewBox="0 0 5 6" style={{ imageRendering: "pixelated" }}>
            <rect x="0" y="0" width="5" height="6" fill="#1a3050" />
            <rect x="0.5" y="0.5" width="4" height="3" fill="#00ff41" opacity="0.8" />
            <rect x="2" y="4" width="1" height="1" fill="#c0ddf0" />
          </svg>
        </div>
      )
    case "music":
      return (
        <motion.div className={base} animate={{ rotate: [-8, 8, -8] }} transition={{ duration: 0.8, repeat: Infinity }}>
          <svg width={16} height={16} viewBox="0 0 5 5" style={{ imageRendering: "pixelated" }}>
            <rect x="0" y="3" width="1" height="2" fill="#ff5577" />
            <rect x="3" y="2" width="1" height="2" fill="#ff5577" />
            <rect x="0" y="0" width="4" height="1" fill="#ff5577" />
            <rect x="3" y="1" width="1" height="1" fill="#ff5577" />
          </svg>
        </motion.div>
      )
    default: return null
  }
}

// ═══ Office props ═══

function Chair({ x, y, color = "#4a7090" }) {
  const s = 5
  const px = (a, b, w = 1, h = 1, c = color) => (
    <rect key={`${a}-${b}-${c}`} x={a*s} y={b*s} width={w*s} height={h*s} fill={c} />
  )
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -20%)" }}>
      <svg width={40} height={36} viewBox="0 0 8 7" style={{ imageRendering: "pixelated" }}>
        {px(1, 0, 6, 1)}{px(1, 1, 1, 4)}{px(6, 1, 1, 4)}
        {px(1, 4, 6, 1, "#1a3050")}
        {px(2, 5, 1, 2, color)}{px(5, 5, 1, 2, color)}
      </svg>
    </div>
  )
}

function WorkDesk({ x, y }) {
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(v => v+1), 160); return () => clearInterval(t)
  }, [])
  const s = 3
  const px = (a, b, w = 1, h = 1, c) => (
    <rect key={`${a}-${b}-${c}`} x={a*s} y={b*s} width={w*s} height={h*s} fill={c} />
  )
  const lit = tick % 3 !== 0
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={72} height={80} viewBox="0 0 16 18" style={{ imageRendering: "pixelated" }}>
        {px(3, 2, 10, 1, "#1a3050")}
        {px(3, 3, 10, 5, "#0b1525")}
        {px(4, 4, 8, 3, lit ? "#00ddcc" : "#0b1525")}
        {px(5, 5, 2, 1, "#ffff00")}
        {px(8, 5, 3, 1, "#00ff41")}
        {px(7, 8, 2, 1, "#1a3050")}
        {px(1, 10, 14, 1, "#4a7090")}
        {px(1, 11, 14, 1, "#1a3050")}
        {px(2, 12, 1, 5, "#4a7090")}
        {px(13, 12, 1, 5, "#4a7090")}
        {/* keyboard */}
        {px(5, 11, 6, 1, "#c0ddf0")}
      </svg>
    </div>
  )
}

function ServerRack({ x, y }) {
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(v => v+1), 240); return () => clearInterval(t)
  }, [])
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={54} height={82} viewBox="0 0 12 18" style={{ imageRendering: "pixelated" }}>
        <rect x="1" y="0" width="10" height="17" fill="#1a3050" />
        <rect x="2" y="1" width="8" height="15" fill="#0b1525" />
        {[0,1,2,3,4,5].map(i => (
          <g key={i}>
            <rect x="3" y={2+i*2.3} width="1" height="1" fill={((tick+i) % 4 !== 0) ? "#00ff41" : "#0b1525"} />
            <rect x="5" y={2+i*2.3} width="1" height="1" fill={((tick+i+1) % 3 === 0) ? "#ff8800" : "#0b1525"} />
            <rect x="7" y={2+i*2.3} width="1" height="1" fill={((tick+i*2) % 5 === 0) ? "#00ffff" : "#0b1525"} />
          </g>
        ))}
        <rect x="1" y="17" width="10" height="1" fill="#4a7090" />
      </svg>
    </div>
  )
}

function Plant({ x, y }) {
  const c = 3.5
  const px = (a, b, w = 1, h = 1, col) => (
    <rect key={`${a}-${b}-${col}`} x={a*c} y={b*c} width={w*c} height={h*c} fill={col} />
  )
  return (
    <motion.div
      className="absolute pointer-events-none"
      style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}
      animate={{ rotate: [-3, 3, -3] }}
      transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
    >
      <svg width={44} height={50} viewBox="0 0 8 9" style={{ imageRendering: "pixelated" }}>
        {px(2, 0, 1, 1, "#00ff41")}{px(1, 1, 2, 1, "#00ff41")}
        {px(4, 1, 2, 1, "#00ff41")}{px(3, 2, 3, 1, "#00ff41")}
        {px(2, 3, 4, 1, "#88ff00")}{px(3, 4, 1, 2, "#4a7090")}
        {px(2, 6, 4, 1, "#ff8800")}{px(2, 7, 4, 2, "#cc5500")}
      </svg>
    </motion.div>
  )
}

function CoffeeMug({ x, y }) {
  const [steam, setSteam] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setSteam(s => s+1), 400); return () => clearInterval(t)
  }, [])
  const c = 3
  const px = (a, b, w = 1, h = 1, col) => (
    <rect key={`${a}-${b}-${col}`} x={a*c} y={b*c} width={w*c} height={h*c} fill={col} />
  )
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={34} height={44} viewBox="0 0 8 10" style={{ imageRendering: "pixelated" }}>
        {[0, 1, 2].map(i => (((steam + i) % 3) === 0) && (
          <rect key={"s"+i} x={2+i} y={0} width="1" height="2" fill="#c0ddf0" opacity="0.4" />
        ))}
        {px(1, 3, 5, 1, "#c0ddf0")}{px(1, 4, 5, 4, "#c0ddf0")}
        {px(2, 4, 3, 1, "#6b4020")}{px(6, 5, 1, 2, "#c0ddf0")}
        {px(2, 8, 3, 1, "#4a7090")}
      </svg>
    </div>
  )
}

function Whiteboard({ x, y }) {
  // pixel "chart" on the board
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(v => v+1), 600); return () => clearInterval(t)
  }, [])
  const bars = useMemo(() =>
    Array.from({ length: 8 }, (_, i) => 1 + Math.floor(Math.abs(Math.sin(i*0.9 + tick*0.4)) * 5)),
    [tick]
  )
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={88} height={60} viewBox="0 0 20 14" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="0" width="20" height="14" fill="#1a3050" />
        <rect x="1" y="1" width="18" height="10" fill="#0b1525" />
        {bars.map((h, i) => (
          <rect key={i} x={2+i*2} y={10-h} width="1" height={h} fill={i%2 ? "#00ff41" : "#00ffff"} />
        ))}
        <line x1="1" y1="10" x2="19" y2="10" stroke="#4a7090" strokeWidth="0.3"/>
        <rect x="2" y="13" width="1" height="1" fill="#4a7090" />
        <rect x="17" y="13" width="1" height="1" fill="#4a7090" />
      </svg>
    </div>
  )
}

function WallClock({ x, y }) {
  const [sec, setSec] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setSec(s => (s+1) % 60), 1000); return () => clearInterval(t)
  }, [])
  const angle = (sec / 60) * 2 * Math.PI
  const hx = Math.sin(angle) * 4
  const hy = -Math.cos(angle) * 4
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={44} height={44} viewBox="-8 -8 16 16" style={{ imageRendering: "pixelated" }}>
        <rect x="-6" y="-6" width="12" height="12" fill="#1a3050" />
        <rect x="-5" y="-5" width="10" height="10" fill="#c0ddf0" />
        <rect x="-1" y="-1" width="2" height="2" fill="#1a3050" />
        <line x1="0" y1="0" x2={hx} y2={hy} stroke="#1a3050" strokeWidth="0.8" />
        <rect x="-0.5" y="-4" width="1" height="1" fill="#ff3333" />
      </svg>
    </div>
  )
}

function FilingCabinet({ x, y }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={44} height={60} viewBox="0 0 8 12" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="0" width="8" height="12" fill="#4a7090" />
        <rect x="1" y="1" width="6" height="3" fill="#2a4060" />
        <rect x="1" y="5" width="6" height="3" fill="#2a4060" />
        <rect x="1" y="9" width="6" height="2" fill="#2a4060" />
        <rect x="3" y="2" width="2" height="1" fill="#c0ddf0" />
        <rect x="3" y="6" width="2" height="1" fill="#c0ddf0" />
        <rect x="3" y="10" width="2" height="0.5" fill="#c0ddf0" />
      </svg>
    </div>
  )
}

function useDrift(seed) {
  const [t, setT] = useState(0)
  useEffect(() => {
    let raf, start = performance.now()
    const loop = (now) => { setT((now - start) / 1000 + seed * 17); raf = requestAnimationFrame(loop) }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [seed])
  return t
}

function MiniMonitor({ color, active }) {
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(x => x+1), 130); return () => clearInterval(t)
  }, [])
  const cells = useMemo(() => {
    const rng = (seed) => (Math.sin(seed*12.345 + tick*0.37) + 1) / 2
    return Array.from({ length: 24 }, (_, i) => rng(i) > (active ? 0.55 : 0.78) ? 1 : 0)
  }, [tick, active])
  return (
    <div className="grid gap-[1px] p-[2px] border" style={{
      gridTemplateColumns: "repeat(6, 2px)",
      borderColor: active ? color : "rgba(74,112,144,0.35)",
      background: "rgba(0,0,0,0.6)",
      boxShadow: active ? `0 0 6px ${color}88` : "none",
    }}>
      {cells.map((v, i) => (
        <span key={i} style={{ width: 2, height: 2, background: v ? color : "rgba(74,112,144,0.15)" }} />
      ))}
    </div>
  )
}

// ═══ Sleek pixel UFO sprite (trendier, cleaner design) ═══
function BigUfoSprite({ size = 120, body = "#00ddcc", dome = "#88ff00", lights = "#ffff00", blink = 0 }) {
  const W = 24, H = 14
  const px = (a, b, w = 1, h = 1, c) => (
    <rect key={`${a}-${b}-${c}-${w}-${h}`} x={a} y={b} width={w} height={h} fill={c} />
  )
  const eyeOpen = blink % 8 !== 0
  return (
    <svg
      width={size}
      height={size * (H/W)}
      viewBox={`0 0 ${W} ${H}`}
      style={{ imageRendering: "pixelated" }}
    >
      {/* ── DOME (glass bubble) ── */}
      {px(10, 0, 4, 1, "#1a3050")}
      {px( 9, 1, 6, 1, dome)}
      {px( 8, 2, 8, 1, dome)}
      {px( 8, 3, 8, 1, dome)}
      {/* dome highlight */}
      {px( 9, 1, 2, 1, "#ffffff")}
      {px( 9, 2, 1, 1, "#ffffff")}

      {/* ── ALIEN inside dome (cute) ── */}
      {/* antenna */}
      {px(11, 0, 2, 1, "#1a3050")}
      {/* head */}
      {px(10, 2, 4, 1, "#88ff00")}
      {/* eyes */}
      {eyeOpen && <>{px(11, 3, 1, 1, "#1a3050")}{px(12, 3, 1, 1, "#1a3050")}</>}

      {/* ── SAUCER top rim ── */}
      {px( 6, 4, 12, 1, body)}

      {/* ── SAUCER main disc with portholes ── */}
      {px( 5, 5,  1, 1, body)}
      {px( 6, 5,  1, 1, lights)}
      {px( 7, 5,  2, 1, body)}
      {px( 9, 5,  1, 1, lights)}
      {px(10, 5,  2, 1, body)}
      {px(12, 5,  1, 1, lights)}
      {px(13, 5,  2, 1, body)}
      {px(15, 5,  1, 1, lights)}
      {px(16, 5,  2, 1, body)}

      {/* ── SAUCER widest belly row ── */}
      {px( 3, 6, 18, 1, body)}
      {/* dark edge */}
      {px( 2, 7, 20, 1, "#1a3050")}
      {px( 3, 7, 18, 1, body)}

      {/* ── BOTTOM hull (darkened, tapers inward) ── */}
      {px( 5, 8, 14, 1, "#0a8a85")}
      {px( 7, 9, 10, 1, "#0a8a85")}
      {px( 9,10,  6, 1, "#0a8a85")}

      {/* ── emitter dot ── */}
      {px(11,11,  2, 1, "#ffffff")}
    </svg>
  )
}

// ═══ Celebration UFO Squadron — 3 UFOs descend together ═══
function CelebrationUFO({ id }) {
  const [blink, setBlink] = useState(0)
  const [beamHue, setBeamHue] = useState(0)

  useEffect(() => {
    if (!id) return
    audio.ufoArrive()
    setTimeout(() => audio.coinDrop(), 900)
    setTimeout(() => audio.partyMusic(), 200)
    const blinkT = setInterval(() => setBlink(v => v+1), 300)
    const hueT   = setInterval(() => setBeamHue(h => (h + 25) % 360), 140)
    return () => { clearInterval(blinkT); clearInterval(hueT) }
  }, [id])

  if (!id) return null

  // 3 UFOs: left small, center big, right medium
  const ships = [
    { leftPct: 28, size: 110, scheme: { body: "#cc44ff", dome: "#00ffff", lights: "#ff5577" }, hueOffset:   0, delay: 0.2,  topKF: ["-20%", "18%", "18%", "18%", "18%", "-25%"] },
    { leftPct: 50, size: 200, scheme: { body: "#00ddcc", dome: "#88ff00", lights: "#ffff00" }, hueOffset:  60, delay: 0,    topKF: ["-30%", "15%", "15%", "15%", "15%", "-35%"] },
    { leftPct: 72, size: 130, scheme: { body: "#ff8800", dome: "#ffff00", lights: "#00ff41" }, hueOffset: 120, delay: 0.4,  topKF: ["-25%", "22%", "22%", "22%", "22%", "-30%"] },
  ]

  return (
    <>
      {ships.map((ship, idx) => (
        <SquadronShip
          key={`${id}-${idx}`}
          ship={ship}
          blink={blink}
          beamHue={(beamHue + ship.hueOffset) % 360}
          showFloorPool={idx === 1}
        />
      ))}
    </>
  )
}

function SquadronShip({ ship, blink, beamHue, showFloorPool }) {
  const ufoW = ship.size
  const ufoH = ufoW * (14/24)
  const beamTop = ufoH - 6
  const beamW = ufoW
  const { leftPct, scheme, delay, topKF } = ship

  return (
    <motion.div
      className="absolute pointer-events-none"
      style={{ zIndex: 8, width: ufoW, left: `${leftPct}%`, marginLeft: -ufoW/2 }}
      initial={{ top: topKF[0], opacity: 0 }}
      animate={{
        top: topKF,
        opacity: [0, 1, 1, 1, 1, 0],
      }}
      transition={{ duration: 4.2, delay, times: [0, 0.15, 0.35, 0.65, 0.85, 1], ease: "easeInOut" }}
    >
      <div className="relative" style={{ width: ufoW, height: ufoH }}>
        {/* Glow halo */}
        <motion.div
          className="absolute blur-xl"
          style={{
            inset: -20,
            background: "radial-gradient(circle, rgba(255,255,0,0.6), rgba(255,255,0,0.15) 40%, transparent 70%)",
          }}
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
        />
        {/* Wobble UFO */}
        <motion.div
          animate={{ y: [0, -5, 0], rotate: [-3, 3, -3] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          style={{ transformOrigin: "center center" }}
        >
          <BigUfoSprite
            size={ufoW}
            body={scheme.body}
            dome={scheme.dome}
            lights={scheme.lights}
            blink={blink}
          />
        </motion.div>

        {/* Beam — straight down · multi-color cycling rainbow */}
        <motion.div
          className="absolute pointer-events-none"
          initial={{ opacity: 0, scaleY: 0.2 }}
          animate={{
            opacity: [0, 0, 0.95, 0.95, 0.95, 0],
            scaleY:  [0.2, 0.3, 1, 1, 1, 0.2],
          }}
          transition={{ duration: 4.2, times: [0, 0.22, 0.38, 0.65, 0.85, 1] }}
          style={{
            top: beamTop,
            left: "50%",
            width: beamW,
            marginLeft: -beamW/2,
            height: 520,
            background: `linear-gradient(to bottom,
              hsla(${beamHue}, 95%, 70%, 0.95),
              hsla(${(beamHue+60)%360}, 95%, 65%, 0.75),
              hsla(${(beamHue+120)%360}, 95%, 65%, 0.55),
              hsla(${(beamHue+180)%360}, 95%, 65%, 0.25))`,
            transformOrigin: "top center",
            filter: `drop-shadow(0 0 60px hsla(${beamHue}, 95%, 60%, 0.85))`,
            WebkitMaskImage: "linear-gradient(to bottom, black 0%, black 78%, transparent 100%)",
            maskImage: "linear-gradient(to bottom, black 0%, black 78%, transparent 100%)",
            clipPath: "polygon(18% 0, 82% 0, 140% 100%, -40% 100%)",
            transition: "background 0.14s linear, filter 0.14s linear",
          }}
        />

        {/* Floor light-pool under UFO (only center ship) */}
        {showFloorPool && (
          <motion.div
            className="absolute pointer-events-none"
            initial={{ opacity: 0, scale: 0.2 }}
            animate={{
              opacity: [0, 0, 0.75, 0.75, 0.75, 0],
              scale:   [0.2, 0.3, 1.2, 1.2, 1.2, 0.4],
            }}
            transition={{ duration: 4.2, times: [0, 0.22, 0.4, 0.65, 0.85, 1] }}
            style={{
              top: beamTop + 480,
              left: "50%",
              width: 360,
              height: 80,
              marginLeft: -180,
              background: `radial-gradient(ellipse, hsla(${beamHue}, 95%, 70%, 0.7), hsla(${(beamHue+90)%360}, 95%, 65%, 0.2) 60%, transparent 100%)`,
              filter: `drop-shadow(0 0 40px hsla(${beamHue}, 95%, 60%, 0.8))`,
              borderRadius: "50%",
              transition: "background 0.14s linear, filter 0.14s linear",
            }}
          />
        )}

        {/* Pulsing rings descending through beam */}
        {[0,1,2,3,4].map(i => (
          <motion.div
            key={i}
            className="absolute pointer-events-none"
            initial={{ opacity: 0, top: beamTop + 4 }}
            animate={{
              opacity: [0, 0.9, 0.9, 0],
              top: [beamTop + 4, beamTop + 380],
            }}
            transition={{
              duration: 1.2,
              delay: 1.0 + i * 0.35,
              ease: "easeIn",
            }}
            style={{
              left: "50%",
              width: beamW + 60,
              marginLeft: -(beamW + 60) / 2,
              height: 6,
              background: `linear-gradient(to right, transparent, hsla(${(beamHue + i*40)%360}, 95%, 80%, 0.95), transparent)`,
              filter: "blur(1px)",
            }}
          />
        ))}

        {/* Circling little sparks around UFO */}
        {[0, 1, 2].map(i => (
          <motion.div
            key={"spark"+i}
            className="absolute pointer-events-none"
            style={{ left: "50%", top: "50%", width: 0, height: 0 }}
            animate={{ rotate: 360 }}
            transition={{ duration: 2 + i * 0.4, repeat: Infinity, ease: "linear" }}
          >
            <span
              className="absolute rounded-full"
              style={{
                left: ufoW * 0.55 + i * 4,
                top: -3,
                width: 4, height: 4,
                background: ["#ffff00", "#00ffff", "#ff5577"][i],
                boxShadow: `0 0 8px ${["#ffff00", "#00ffff", "#ff5577"][i]}`,
              }}
            />
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}

// ═══ More office props ═══
function Printer({ x, y }) {
  const [tick, setTick] = useState(0)
  useEffect(() => { const t = setInterval(() => setTick(v => v+1), 700); return () => clearInterval(t) }, [])
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={54} height={48} viewBox="0 0 18 16" style={{ imageRendering: "pixelated" }}>
        <rect x="1" y="2" width="16" height="9" fill="#4a7090" />
        <rect x="2" y="3" width="14" height="2" fill="#1a3050" />
        <rect x="3" y="4" width="1" height="1" fill="#00ff41" />
        <rect x="5" y="4" width="1" height="1" fill={tick%2 ? "#ff8800" : "#0b1525"} />
        <rect x="2" y="6" width="14" height="4" fill="#c0ddf0" />
        <rect x="4" y="7" width="10" height="0.5" fill="#1a3050" />
        <rect x="4" y="8" width="10" height="0.5" fill="#1a3050" />
        <rect x="2" y="11" width="16" height="2" fill="#2a4060" />
        <rect x="4" y="14" width="10" height="2" fill="#c0ddf0" />
      </svg>
    </div>
  )
}

function WaterCooler({ x, y }) {
  const [bub, setBub] = useState(0)
  useEffect(() => { const t = setInterval(() => setBub(v => v+1), 500); return () => clearInterval(t) }, [])
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={30} height={56} viewBox="0 0 10 18" style={{ imageRendering: "pixelated" }}>
        <rect x="2" y="0" width="6" height="6" fill="#00ddcc" opacity="0.7" />
        <rect x="2" y="0" width="6" height="1" fill="#4a7090" />
        {bub%3===0 && <rect x="4" y="3" width="1" height="1" fill="#ffffff" opacity="0.9" />}
        {bub%2===0 && <rect x="6" y="4" width="1" height="1" fill="#ffffff" opacity="0.9" />}
        <rect x="1" y="6" width="8" height="2" fill="#c0ddf0" />
        <rect x="2" y="8" width="6" height="9" fill="#c0ddf0" />
        <rect x="4" y="10" width="2" height="1" fill="#4a7090" />
        <rect x="1" y="17" width="8" height="1" fill="#1a3050" />
      </svg>
    </div>
  )
}

function Bookshelf({ x, y }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={64} height={80} viewBox="0 0 16 20" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="0" width="16" height="20" fill="#6b4020" />
        <rect x="1" y="1" width="14" height="4" fill="#4a2c10" />
        <rect x="1" y="6" width="14" height="4" fill="#4a2c10" />
        <rect x="1" y="11" width="14" height="4" fill="#4a2c10" />
        <rect x="1" y="16" width="14" height="3" fill="#4a2c10" />
        {/* books row 1 */}
        {["#ff3333","#00ff41","#00ffff","#ffff00","#cc44ff","#ff8800","#ff5577"].map((c,i)=>(
          <rect key={"b1"+i} x={1+i*2} y={1} width="2" height="4" fill={c} />
        ))}
        {/* books row 2 */}
        {["#00ffff","#ffff00","#00ff41","#cc44ff","#ff8800","#ff3333"].map((c,i)=>(
          <rect key={"b2"+i} x={1+i*2.2} y={6} width={i<5 ? 2 : 3} height="4" fill={c} />
        ))}
        {/* plant on top */}
        <rect x="6" y="11" width="4" height="4" fill="#00ff41" />
        <rect x="5" y="13" width="2" height="2" fill="#6b4020" />
        {/* trophy */}
        <rect x="12" y="12" width="2" height="3" fill="#ffff00" />
        <rect x="11" y="15" width="4" height="1" fill="#ffff00" />
      </svg>
    </div>
  )
}

function Couch({ x, y }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={80} height={36} viewBox="0 0 20 9" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="1" width="20" height="5" fill="#cc44ff" />
        <rect x="0" y="0" width="3" height="6" fill="#aa33dd" />
        <rect x="17" y="0" width="3" height="6" fill="#aa33dd" />
        <rect x="3" y="4" width="14" height="2" fill="#8822bb" />
        {/* cushion lines */}
        <rect x="6" y="2" width="0.5" height="3" fill="#8822bb" />
        <rect x="12" y="2" width="0.5" height="3" fill="#8822bb" />
        {/* legs */}
        <rect x="2" y="7" width="1" height="1" fill="#1a3050" />
        <rect x="17" y="7" width="1" height="1" fill="#1a3050" />
      </svg>
    </div>
  )
}

function WindowView({ x, y }) {
  const [t, setT] = useState(0)
  useEffect(() => { const i = setInterval(() => setT(v => v+1), 300); return () => clearInterval(i) }, [])
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={90} height={60} viewBox="0 0 18 12" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="0" width="18" height="12" fill="#1a3050" />
        <rect x="1" y="1" width="16" height="10" fill="#050a14" />
        {/* stars */}
        {[[3,2],[7,3],[12,2],[15,4],[5,5],[10,6],[14,7],[4,8],[9,9]].map(([sx,sy], i) => (
          <rect key={i} x={sx} y={sy} width="0.5" height="0.5"
            fill="#ffffff" opacity={((t+i)%3===0) ? 1 : 0.4} />
        ))}
        {/* planet */}
        <circle cx="13" cy="8" r="1.2" fill="#00ff41" />
        <rect x="12.5" y="7.5" width="0.6" height="0.3" fill="#88ff00" />
        {/* mullions */}
        <line x1="9" y1="1" x2="9" y2="11" stroke="#1a3050" strokeWidth="0.3" />
        <line x1="1" y1="6" x2="17" y2="6" stroke="#1a3050" strokeWidth="0.3" />
      </svg>
    </div>
  )
}

function Poster({ x, y, text = "HODL", color = "#ffff00" }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={52} height={40} viewBox="0 0 13 10" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="0" width="13" height="10" fill="#1a3050" />
        <rect x="1" y="1" width="11" height="8" fill="#0b1525" />
        {/* ascending arrow */}
        <rect x="2" y="6" width="1" height="1" fill={color} />
        <rect x="3" y="5" width="1" height="2" fill={color} />
        <rect x="4" y="4" width="1" height="3" fill={color} />
        <rect x="5" y="3" width="1" height="4" fill={color} />
        <rect x="6" y="2" width="1" height="5" fill={color} />
        <rect x="7" y="3" width="1" height="4" fill={color} />
        <rect x="8" y="2" width="1" height="5" fill={color} />
        <rect x="9" y="1" width="1" height="6" fill={color} />
      </svg>
    </div>
  )
}

function TrashCan({ x, y }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={26} height={32} viewBox="0 0 8 10" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="1" width="8" height="1" fill="#4a7090" />
        <rect x="1" y="2" width="6" height="8" fill="#2a4060" />
        <rect x="2" y="3" width="1" height="6" fill="#4a7090" />
        <rect x="5" y="3" width="1" height="6" fill="#4a7090" />
      </svg>
    </div>
  )
}

function ArcadeMachine({ x, y }) {
  const [t, setT] = useState(0)
  useEffect(() => { const i = setInterval(() => setT(v => v+1), 200); return () => clearInterval(i) }, [])
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={36} height={70} viewBox="0 0 9 18" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="0" width="9" height="18" fill="#ff3333" />
        <rect x="1" y="1" width="7" height="2" fill="#ffff00" />
        <rect x="1" y="4" width="7" height="6" fill="#0b1525" />
        {/* screen content */}
        <rect x="2" y="5" width={((t%4)+1)} height="1" fill="#00ff41" />
        <rect x="2" y="7" width={((t%3)+2)} height="1" fill="#00ffff" />
        <rect x="2" y="9" width={((t%5)+1)} height="0.5" fill="#ffff00" />
        {/* joystick + buttons */}
        <rect x="2" y="12" width="2" height="2" fill="#1a3050" />
        <rect x="2.5" y="11" width="1" height="1" fill="#ff8800" />
        <rect x="5" y="12" width="1" height="1" fill="#00ff41" />
        <rect x="6.5" y="12" width="1" height="1" fill="#ff3333" />
        {/* body stripe */}
        <rect x="0" y="15" width="9" height="1" fill="#ffff00" />
      </svg>
    </div>
  )
}

function StandingDesk({ x, y }) {
  const [tick, setTick] = useState(0)
  useEffect(() => { const t = setInterval(() => setTick(v => v+1), 200); return () => clearInterval(t) }, [])
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={72} height={66} viewBox="0 0 18 16" style={{ imageRendering: "pixelated" }}>
        {/* dual monitors */}
        <rect x="2" y="1" width="6" height="5" fill="#1a3050" />
        <rect x="3" y="2" width="4" height="3" fill={tick%2 ? "#00ff41" : "#00ffff"} />
        <rect x="10" y="1" width="6" height="5" fill="#1a3050" />
        <rect x="11" y="2" width="4" height="3" fill={tick%3 ? "#ffff00" : "#ff5577"} />
        <rect x="4" y="6" width="2" height="1" fill="#1a3050" />
        <rect x="12" y="6" width="2" height="1" fill="#1a3050" />
        {/* desk surface */}
        <rect x="0" y="8" width="18" height="1" fill="#6b4020" />
        <rect x="0" y="9" width="18" height="1" fill="#4a2c10" />
        {/* adjustable leg */}
        <rect x="8" y="10" width="2" height="5" fill="#4a7090" />
        <rect x="7" y="15" width="4" height="1" fill="#1a3050" />
        {/* keyboard */}
        <rect x="6" y="7" width="6" height="1" fill="#c0ddf0" />
      </svg>
    </div>
  )
}

function Fridge({ x, y }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={40} height={72} viewBox="0 0 10 18" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="0" width="10" height="18" fill="#c0ddf0" />
        <rect x="1" y="1" width="8" height="5" fill="#a0c0d0" />
        <rect x="1" y="7" width="8" height="10" fill="#a0c0d0" />
        <rect x="7" y="3" width="1" height="1" fill="#1a3050" />
        <rect x="7" y="11" width="1" height="1" fill="#1a3050" />
        {/* magnets */}
        <rect x="2" y="3" width="1" height="1" fill="#ff3333" />
        <rect x="4" y="4" width="1" height="1" fill="#00ff41" />
        {/* note */}
        <rect x="3" y="10" width="3" height="2" fill="#ffff00" />
      </svg>
    </div>
  )
}

function VendingMachine({ x, y }) {
  const [t, setT] = useState(0)
  useEffect(() => { const i = setInterval(() => setT(v => v+1), 500); return () => clearInterval(i) }, [])
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={50} height={88} viewBox="0 0 10 18" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="0" width="10" height="18" fill="#ff3333" />
        <rect x="1" y="1" width="8" height="12" fill="#0b1525" />
        {/* product slots */}
        {[0,1,2].map(row => (
          [0,1,2].map(col => {
            const colors = ["#ffff00","#00ff41","#00ffff","#ff8800","#cc44ff","#88ff00","#ff5577","#ff3333","#00ddcc"]
            return <rect key={`${row}-${col}`} x={1.5+col*2.5} y={1.5+row*4} width="1.5" height="3"
              fill={colors[(row*3+col+Math.floor(t/3))%9]} />
          })
        ))}
        {/* display */}
        <rect x="2" y="14" width="6" height="2" fill="#00ff41" opacity="0.4" />
        <rect x="3" y="14.5" width="1" height="1" fill="#00ff41" />
        <rect x="5" y="14.5" width="1" height="1" fill="#00ff41" />
        {/* slot */}
        <rect x="2" y="16" width="6" height="1" fill="#1a3050" />
      </svg>
    </div>
  )
}

function WallTV({ x, y }) {
  const [t, setT] = useState(0)
  useEffect(() => { const i = setInterval(() => setT(v => v+1), 250); return () => clearInterval(i) }, [])
  const bars = Array.from({ length: 9 }, (_, i) => 1 + Math.floor(Math.abs(Math.sin(i*1.1 + t*0.3)) * 4))
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={84} height={52} viewBox="0 0 21 13" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="0" width="21" height="13" fill="#1a3050" />
        <rect x="1" y="1" width="19" height="10" fill="#0b1525" />
        {/* live indicator */}
        <rect x="17" y="2" width="1" height="1" fill="#ff3333" style={{ opacity: t%2 ? 1 : 0.3 }} />
        {/* ticker line */}
        <rect x="2" y="3" width="12" height="0.4" fill="#00ff41" />
        {/* bars */}
        {bars.map((h, i) => (
          <rect key={i} x={2+i*1.8} y={10-h} width="1.2" height={h}
            fill={i%2 ? "#00ff41" : "#00ffff"} />
        ))}
        {/* stand */}
        <rect x="9" y="11" width="3" height="1" fill="#1a3050" />
        <rect x="7" y="12" width="7" height="1" fill="#1a3050" />
      </svg>
    </div>
  )
}

function Lockers({ x, y }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={80} height={74} viewBox="0 0 20 18" style={{ imageRendering: "pixelated" }}>
        {[0,1,2,3].map(i => (
          <g key={i}>
            <rect x={i*5} y="0" width="4.5" height="17" fill="#4a7090" />
            <rect x={i*5+0.5} y="0.5" width="3.5" height="16" fill={["#cc44ff","#00ddcc","#ff8800","#88ff00"][i]} />
            <rect x={i*5+1} y="1" width="2.5" height="15" fill={["#aa33dd","#00aa99","#cc6600","#66cc00"][i]} />
            {/* handle + number */}
            <rect x={i*5+1.5} y="8" width="1" height="1" fill="#1a3050" />
            <rect x={i*5+2} y="2" width="1" height="1" fill="#ffffff" />
          </g>
        ))}
        <rect x="0" y="17" width="20" height="1" fill="#1a3050" />
      </svg>
    </div>
  )
}

function Microwave({ x, y }) {
  const [t, setT] = useState(0)
  useEffect(() => { const i = setInterval(() => setT(v => (v+1) % 60), 1000); return () => clearInterval(i) }, [])
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={44} height={30} viewBox="0 0 12 8" style={{ imageRendering: "pixelated" }}>
        <rect x="0" y="0" width="12" height="8" fill="#4a7090" />
        <rect x="1" y="1" width="7" height="6" fill="#0b1525" />
        <rect x="2" y="2" width="5" height="4" fill="#2a4060" />
        {/* plate */}
        <ellipse cx="4.5" cy="4.5" rx="2" ry="0.5" fill="#c0ddf0" />
        {/* control panel */}
        <rect x="9" y="1" width="3" height="2" fill="#0b1525" />
        <rect x="9.5" y="1.5" width="2" height="1" fill="#00ff41" />
        <rect x="9" y="4" width="1" height="1" fill="#ff3333" />
        <rect x="11" y="4" width="1" height="1" fill="#00ff41" />
        <rect x="10" y="6" width="1" height="1" fill={t%2 ? "#ffff00" : "#1a3050"} />
      </svg>
    </div>
  )
}

function PingPongTable({ x, y }) {
  const [t, setT] = useState(0)
  useEffect(() => { const i = setInterval(() => setT(v => v+1), 400); return () => clearInterval(i) }, [])
  const ballX = 3 + Math.abs(Math.sin(t * 0.5)) * 8
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={72} height={34} viewBox="0 0 18 8" style={{ imageRendering: "pixelated" }}>
        {/* table top */}
        <rect x="0" y="2" width="18" height="3" fill="#00aa44" />
        <rect x="0" y="2" width="18" height="0.3" fill="#ffffff" />
        <rect x="8.9" y="2" width="0.3" height="3" fill="#ffffff" />
        {/* legs */}
        <rect x="1" y="5" width="1" height="3" fill="#1a3050" />
        <rect x="16" y="5" width="1" height="3" fill="#1a3050" />
        {/* paddles */}
        <rect x="0.5" y="1" width="1" height="1.5" fill="#ff3333" />
        <rect x="16.5" y="1" width="1" height="1.5" fill="#0088ff" />
        {/* bouncing ball */}
        <circle cx={ballX} cy={1 - Math.abs(Math.sin(t*0.8))} r="0.4" fill="#ffffff" />
      </svg>
    </div>
  )
}

function Dartboard({ x, y }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={36} height={36} viewBox="-10 -10 20 20" style={{ imageRendering: "pixelated" }}>
        <circle r="9" fill="#1a3050" />
        <circle r="8" fill="#ff3333" />
        <circle r="6" fill="#ffffff" />
        <circle r="4" fill="#ff3333" />
        <circle r="2" fill="#ffffff" />
        <circle r="0.8" fill="#00ff41" />
        {/* darts */}
        <rect x="3" y="-1" width="2" height="0.3" fill="#ffff00" />
        <rect x="2.5" y="-1.2" width="0.5" height="0.7" fill="#ff3333" />
      </svg>
    </div>
  )
}

// Full kitchen unit — counter + stove + sink + cabinets
function KitchenUnit({ x, y }) {
  const [t, setT] = useState(0)
  useEffect(() => { const i = setInterval(() => setT(v => v+1), 350); return () => clearInterval(i) }, [])
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={180} height={90} viewBox="0 0 36 18" style={{ imageRendering: "pixelated" }}>
        {/* overhead cabinets */}
        <rect x="0" y="0" width="36" height="4" fill="#6b4020" />
        <rect x="1" y="1" width="7" height="2.5" fill="#4a2c10" />
        <rect x="9" y="1" width="7" height="2.5" fill="#4a2c10" />
        <rect x="17" y="1" width="7" height="2.5" fill="#4a2c10" />
        <rect x="25" y="1" width="7" height="2.5" fill="#4a2c10" />
        <rect x="4" y="2" width="0.5" height="1" fill="#c0ddf0" />
        <rect x="12" y="2" width="0.5" height="1" fill="#c0ddf0" />
        <rect x="20" y="2" width="0.5" height="1" fill="#c0ddf0" />
        <rect x="28" y="2" width="0.5" height="1" fill="#c0ddf0" />
        {/* countertop */}
        <rect x="0" y="8" width="36" height="1.5" fill="#c0ddf0" />
        {/* sink */}
        <rect x="2" y="9" width="7" height="2.5" fill="#4a7090" />
        <rect x="3" y="9.5" width="5" height="1.5" fill="#2a4060" />
        <rect x="5" y="8.2" width="0.5" height="0.8" fill="#4a7090" />
        {t%3===0 && <rect x="5.5" y="9.7" width="0.5" height="0.3" fill="#00ffff" opacity="0.7" />}
        {/* stove */}
        <rect x="12" y="9" width="10" height="2.5" fill="#1a3050" />
        <rect x="13" y="9.5" width="2" height="1.5" fill={t%2 ? "#ff5500" : "#1a3050"} />
        <rect x="16" y="9.5" width="2" height="1.5" fill="#1a3050" />
        <rect x="19" y="9.5" width="2" height="1.5" fill={t%4===0 ? "#ff5500" : "#1a3050"} />
        {/* pots on stove */}
        {t%2===0 && <rect x="13.2" y="8.5" width="1.6" height="1" fill="#c0ddf0" />}
        <rect x="16.2" y="8.5" width="1.6" height="1" fill="#4a7090" />
        {/* steam from pot */}
        {t%2===0 && <>
          <rect x="14" y="7" width="0.4" height="1" fill="#c0ddf0" opacity="0.5" />
          <rect x="13.6" y="7.6" width="0.4" height="0.6" fill="#c0ddf0" opacity="0.4" />
        </>}
        {/* coffee machine */}
        <rect x="25" y="7" width="4" height="2" fill="#1a3050" />
        <rect x="26" y="7.5" width="2" height="1" fill={t%2 ? "#00ff41" : "#0b1525"} />
        {/* lower cabinets */}
        <rect x="0" y="9.5" width="36" height="8.5" fill="#6b4020" />
        <rect x="1" y="12" width="10" height="5.5" fill="#4a2c10" />
        <rect x="12" y="12" width="10" height="5.5" fill="#4a2c10" />
        <rect x="23" y="12" width="12" height="5.5" fill="#4a2c10" />
        {/* handles */}
        <rect x="5" y="14" width="2" height="0.5" fill="#ffff00" />
        <rect x="16" y="14" width="2" height="0.5" fill="#ffff00" />
        <rect x="28" y="14" width="2" height="0.5" fill="#ffff00" />
      </svg>
    </div>
  )
}

// Pool / billiards table with balls
function PoolTable({ x, y }) {
  const [t, setT] = useState(0)
  useEffect(() => { const i = setInterval(() => setT(v => v+1), 600); return () => clearInterval(i) }, [])
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={120} height={70} viewBox="0 0 30 16" style={{ imageRendering: "pixelated" }}>
        {/* wood frame */}
        <rect x="0" y="0" width="30" height="16" fill="#4a2c10" />
        <rect x="1" y="1" width="28" height="14" fill="#6b4020" />
        {/* felt */}
        <rect x="2" y="2" width="26" height="12" fill="#00aa44" />
        {/* pockets */}
        {[[2,2],[15,2],[28,2],[2,14],[15,14],[28,14]].map(([px, py], i) => (
          <circle key={i} cx={px} cy={py} r="1.2" fill="#0b1525" />
        ))}
        {/* balls (colored) */}
        <circle cx="8" cy="8" r="0.9" fill="#ffff00" />
        <circle cx={10 + (t%3)*0.5} cy="8" r="0.9" fill="#0088ff" />
        <circle cx="12" cy="7" r="0.9" fill="#ff3333" />
        <circle cx="12" cy="9" r="0.9" fill="#cc44ff" />
        <circle cx="14" cy="8" r="0.9" fill="#ff8800" />
        <circle cx="20" cy="8" r="0.9" fill="#ffffff" />
        <circle cx="18" cy="6.5" r="0.9" fill="#00ff41" />
        <circle cx="18" cy="9.5" r="0.9" fill="#1a3050" />
        {/* cue stick */}
        <rect x="17" y="11" width="10" height="0.3" fill="#c0ddf0" transform="rotate(-8 22 11)" />
      </svg>
    </div>
  )
}

// Pro spot trader desk — 3 monitors with candlestick charts
function TradingDesk({ x, y }) {
  const [t, setT] = useState(0)
  useEffect(() => { const i = setInterval(() => setT(v => v+1), 400); return () => clearInterval(i) }, [])
  // Generate candlestick data
  const candles = (seed, count) =>
    Array.from({ length: count }, (_, i) => {
      const base = 3 + Math.sin((i + seed + Math.floor(t/2)) * 0.7) * 1.5
      const open = base + Math.sin(i + seed) * 0.3
      const close = base + Math.cos(i + seed + 1) * 0.4
      const high = Math.max(open, close) + 0.3
      const low  = Math.min(open, close) - 0.3
      return { open, close, high, low, up: close > open }
    })
  const mon1 = candles(0, 8)
  const mon2 = candles(5, 8)
  const mon3 = candles(10, 6)
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={150} height={90} viewBox="0 0 30 18" style={{ imageRendering: "pixelated" }}>
        {/* desk */}
        <rect x="0" y="13" width="30" height="1" fill="#6b4020" />
        <rect x="0" y="14" width="30" height="1" fill="#4a2c10" />
        <rect x="1"  y="15" width="1" height="3" fill="#4a2c10" />
        <rect x="28" y="15" width="1" height="3" fill="#4a2c10" />

        {/* LEFT monitor */}
        <rect x="1" y="0" width="9" height="7" fill="#1a3050" />
        <rect x="2" y="1" width="7" height="5" fill="#0b1525" />
        {mon1.map((c, i) => (
          <g key={`l${i}`}>
            <rect x={2.3 + i*0.8} y={Math.min(c.high, 6) * 0.5 + 0.5} width="0.1" height={Math.abs(c.high-c.low)*0.5} fill={c.up ? "#00ff41" : "#ff3333"} />
            <rect x={2.2 + i*0.8} y={Math.min(c.open, c.close) * 0.5 + 0.5} width="0.6" height={Math.abs(c.open-c.close)*0.5 + 0.15} fill={c.up ? "#00ff41" : "#ff3333"} />
          </g>
        ))}
        {/* price label */}
        <rect x="2" y="6" width="7" height="0.6" fill="#ffff00" opacity="0.3" />
        <rect x="5.5" y="6" width="0.4" height="0.6" fill="#ffff00" />

        {/* CENTER monitor (bigger) */}
        <rect x="11" y="0" width="8" height="9" fill="#1a3050" />
        <rect x="12" y="1" width="6" height="7" fill="#0b1525" />
        {mon2.map((c, i) => (
          <g key={`c${i}`}>
            <rect x={12.3 + i*0.7} y={Math.min(c.high, 7) * 0.6 + 0.8} width="0.1" height={Math.abs(c.high-c.low)*0.6} fill={c.up ? "#00ff41" : "#ff3333"} />
            <rect x={12.2 + i*0.7} y={Math.min(c.open, c.close) * 0.6 + 0.8} width="0.5" height={Math.abs(c.open-c.close)*0.6 + 0.15} fill={c.up ? "#00ff41" : "#ff3333"} />
          </g>
        ))}
        <rect x="12" y="7.5" width="2" height="0.5" fill="#00ff41" />
        <rect x="14" y="7.5" width="1" height="0.5" fill="#ff3333" />

        {/* RIGHT monitor (orderbook-ish) */}
        <rect x="20" y="0" width="9" height="7" fill="#1a3050" />
        <rect x="21" y="1" width="7" height="5" fill="#0b1525" />
        {/* bid/ask rows */}
        {[0,1,2,3].map(i => (
          <g key={`r${i}`}>
            <rect x="21.2" y={1.4 + i*0.7} width={3 + Math.abs(Math.sin(i+t*0.3))*2} height="0.5" fill="#ff3333" opacity="0.55" />
            <rect x="25"   y={1.4 + i*0.7} width={3 - Math.abs(Math.sin(i+t*0.3))*2} height="0.5" fill="#00ff41" opacity="0.55" />
          </g>
        ))}

        {/* stands */}
        <rect x="5"  y="7" width="1" height="1" fill="#1a3050" />
        <rect x="14" y="9" width="2" height="1" fill="#1a3050" />
        <rect x="24" y="7" width="1" height="1" fill="#1a3050" />

        {/* keyboards on desk */}
        <rect x="3"  y="12" width="5" height="1" fill="#c0ddf0" />
        <rect x="12" y="12" width="6" height="1" fill="#c0ddf0" />
        <rect x="21" y="12" width="6" height="1" fill="#c0ddf0" />

        {/* LED strip under desk — blinking green */}
        {[0,1,2,3,4,5,6,7].map(i => (
          <rect key={`led${i}`} x={3+i*3.5} y="13.4" width="0.4" height="0.3"
            fill={(i + t) % 3 === 0 ? "#00ff41" : "#1a3050"} />
        ))}
      </svg>
    </div>
  )
}

function ConferenceTable({ x, y }) {
  return (
    <div className="absolute pointer-events-none" style={{ left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)" }}>
      <svg width={120} height={40} viewBox="0 0 30 10" style={{ imageRendering: "pixelated" }}>
        <ellipse cx="15" cy="5" rx="14" ry="3.5" fill="#4a2c10" />
        <ellipse cx="15" cy="4.5" rx="13" ry="3" fill="#6b4020" />
        {/* items on table */}
        <rect x="10" y="4" width="2" height="1" fill="#c0ddf0" />
        <rect x="14" y="3.5" width="3" height="1.5" fill="#1a3050" />
        <rect x="14.5" y="4" width="2" height="0.5" fill="#00ff41" />
        <rect x="19" y="4" width="2" height="1" fill="#ff8800" />
        {/* base */}
        <rect x="14" y="7.5" width="2" height="2" fill="#4a2c10" />
      </svg>
    </div>
  )
}

// ═══ Coin rain ═══
function CoinRain({ id }) {
  const coins = useMemo(() => {
    if (!id) return []
    return Array.from({ length: 28 }, (_, i) => ({
      id: `${id}-${i}`,
      x: 15 + Math.random() * 70,
      delay: Math.random() * 1.5,
      duration: 1.5 + Math.random() * 1.2,
      glyph: ["₿","Ξ","◎","♦","¢"][i % 5],
      color: ["#ffff00","#00ff41","#00ffff","#ff8800","#ffff00"][i % 5],
      size: 12 + Math.random() * 6,
      spin: (Math.random() - 0.5) * 720,
    }))
  }, [id])
  if (!id) return null
  return (
    <AnimatePresence>
      {coins.map(c => (
        <motion.span
          key={c.id}
          className="absolute pk pointer-events-none"
          initial={{ top: "-10%", left: `${c.x}%`, opacity: 0, rotate: 0, scale: 0.8 }}
          animate={{
            top: ["-10%", "90%"],
            opacity: [0, 1, 1, 0],
            rotate: c.spin,
            scale: [0.8, 1.1, 0.9],
          }}
          exit={{ opacity: 0 }}
          transition={{ duration: c.duration, delay: c.delay, ease: [0.3, 0, 0.7, 1] }}
          style={{
            fontSize: c.size,
            color: c.color,
            textShadow: `0 0 6px ${c.color}`,
          }}
        >
          {c.glyph}
        </motion.span>
      ))}
    </AnimatePresence>
  )
}

// ═══ Party Club Mode — disco spotlights, flashing lights, dance floor ═══
function PartyClubMode({ active }) {
  const [t, setT] = useState(0)
  useEffect(() => {
    if (!active) return
    const i = setInterval(() => setT(v => v+1), 120)
    return () => clearInterval(i)
  }, [active])

  if (!active) return null

  const colors = ["#ff00ff", "#00ffff", "#ffff00", "#00ff41", "#ff5577", "#cc44ff"]

  return (
    <>
      {/* Club darkener — dims office props subtly */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "rgba(5,10,20,0.55)",
          zIndex: 3,
          animation: "qwr-flicker 2s infinite",
        }}
      />

      {/* Disco spotlight beams — rotating cones from ceiling */}
      {[0, 1, 2, 3, 4].map(i => {
        const angle = (t * 4 + i * 72) % 360
        const col = colors[(i + Math.floor(t / 5)) % colors.length]
        return (
          <div
            key={"beam"+i}
            className="absolute pointer-events-none"
            style={{
              left: `${15 + i * 17.5}%`,
              top: 0,
              width: 80,
              height: 420,
              marginLeft: -40,
              background: `linear-gradient(to bottom, ${col}66, ${col}11, transparent)`,
              transform: `rotate(${Math.sin(angle * Math.PI / 180) * 25}deg)`,
              transformOrigin: "top center",
              clipPath: "polygon(35% 0, 65% 0, 100% 100%, 0 100%)",
              filter: `drop-shadow(0 0 12px ${col})`,
              mixBlendMode: "screen",
              zIndex: 4,
              transition: "transform 0.2s linear",
            }}
          />
        )
      })}

      {/* Ceiling disco ball */}
      <div
        className="absolute pointer-events-none"
        style={{
          left: "50%",
          top: 12,
          width: 36, height: 36,
          marginLeft: -18,
          borderRadius: "50%",
          background: `
            radial-gradient(circle at 30% 30%, #ffffff, #c0ddf0 30%, #4a7090 60%, #1a3050 100%)
          `,
          boxShadow: `
            0 0 12px rgba(255,255,255,0.8),
            0 0 24px ${colors[t % colors.length]}88
          `,
          animation: "qwr-flicker 1.5s infinite",
          zIndex: 6,
        }}
      />
      <div
        className="absolute pointer-events-none"
        style={{
          left: "50%",
          top: 0,
          width: 2, height: 14,
          marginLeft: -1,
          background: "#4a7090",
          zIndex: 5,
        }}
      />

      {/* Wall party lights (pulsing) */}
      {[5, 20, 35, 50, 65, 80, 95].map((xp, i) => {
        const col = colors[(i + Math.floor(t / 3)) % colors.length]
        return (
          <div
            key={"wall"+i}
            className="absolute pointer-events-none"
            style={{
              left: `${xp}%`,
              top: 2,
              width: 14, height: 8,
              marginLeft: -7,
              background: col,
              boxShadow: `0 0 12px ${col}, 0 4px 20px ${col}88`,
              opacity: 0.3 + Math.sin((t + i) * 0.5) * 0.7,
              zIndex: 5,
              transition: "background 0.3s",
            }}
          />
        )
      })}

      {/* Floor dance tiles — pulsing colored squares */}
      {Array.from({ length: 18 }, (_, i) => {
        const col = colors[(i + Math.floor(t / 2)) % colors.length]
        const cx = 10 + (i % 6) * 14
        const cy = 55 + Math.floor(i / 6) * 14
        return (
          <div
            key={"floor"+i}
            className="absolute pointer-events-none"
            style={{
              left: `${cx}%`,
              top: `${cy}%`,
              width: 60,
              height: 40,
              marginLeft: -30,
              marginTop: -20,
              background: col,
              opacity: 0.12 + Math.abs(Math.sin((t + i * 0.5) * 0.3)) * 0.18,
              mixBlendMode: "screen",
              zIndex: 1,
              transition: "background 0.2s",
            }}
          />
        )
      })}

      {/* Rotating strobes from corners */}
      {[[0, 0], [100, 0], [0, 100], [100, 100]].map(([sx, sy], i) => {
        const col = colors[(i * 2 + Math.floor(t / 4)) % colors.length]
        return (
          <div
            key={"strobe"+i}
            className="absolute pointer-events-none"
            style={{
              left: `${sx}%`,
              top: `${sy}%`,
              width: 4,
              height: 4,
              marginLeft: -2,
              marginTop: -2,
              background: col,
              boxShadow: `0 0 30px 8px ${col}, 0 0 60px 12px ${col}66`,
              zIndex: 6,
              animation: "qwr-blink 0.3s infinite",
            }}
          />
        )
      })}
    </>
  )
}

function Confetti({ burst }) {
  const pieces = useMemo(() => {
    if (!burst) return []
    return Array.from({ length: 30 }, (_, i) => ({
      id: `${burst}-${i}`,
      x: 20 + Math.random() * 60, y: 20 + Math.random() * 60,
      dx: (Math.random() - 0.5) * 60, dy: -20 - Math.random() * 50,
      size: 3 + Math.random() * 3,
      color: ["#00ffff","#00ff41","#ffff00","#ff5577","#cc44ff","#ff8800"][i % 6],
      delay: Math.random() * 0.2,
    }))
  }, [burst])
  return (
    <AnimatePresence>
      {pieces.map(p => (
        <motion.span
          key={p.id}
          className="absolute pointer-events-none"
          initial={{ left: `${p.x}%`, top: `${p.y}%`, opacity: 0, scale: 0.5 }}
          animate={{
            left: `${p.x + p.dx/5}%`, top: `${p.y + p.dy/4}%`,
            opacity: [0, 1, 0], scale: 1, rotate: 360,
          }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.2, delay: p.delay, ease: "easeOut" }}
          style={{
            width: p.size, height: p.size,
            background: p.color, boxShadow: `0 0 6px ${p.color}`,
          }}
        />
      ))}
    </AnimatePresence>
  )
}

export default function AgentArena({ activeId, convictions, onSelectAgent }) {
  const wrapRef = useRef(null)
  const [size, setSize] = useState({ w: 1, h: 1 })
  const [pulseEdge, setPulseEdge] = useState(null)
  const [statuses, setStatuses] = useState(() =>
    AGENTS.reduce((acc, a) => { acc[a.id] = "SCAN"; return acc }, {}))
  const [activities, setActivities] = useState(() =>
    AGENTS.reduce((acc, a) => { acc[a.id] = "work"; return acc }, {}))
  const [waypoint, setWaypoint] = useState(() =>
    AGENTS.reduce((acc, a) => { acc[a.id] = 0; return acc }, {}))
  const [moving, setMoving] = useState(() =>
    AGENTS.reduce((acc, a) => { acc[a.id] = false; return acc }, {}))
  const [danceId, setDanceId] = useState(0)
  const [celebrationId, setCelebrationId] = useState(0)
  const [confettiId, setConfettiId] = useState(0)
  const drift = useDrift(1)

  useEffect(() => {
    if (!wrapRef.current) return
    const ro = new ResizeObserver(() => {
      const r = wrapRef.current.getBoundingClientRect()
      setSize({ w: r.width, h: r.height })
    })
    ro.observe(wrapRef.current)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    const t = setInterval(() => {
      const idx = Math.floor(Math.random() * LINES.length)
      setPulseEdge({ idx, id: Date.now() })
      audio.ping()
    }, 800 + Math.random()*700)
    return () => clearInterval(t)
  }, [])

  // Walk cycle — multiple agents moving at once, faster pace
  useEffect(() => {
    const t = setInterval(() => {
      // move 1-2 random agents
      const movers = Array.from({ length: 1 + Math.floor(Math.random() * 2) }, () =>
        AGENTS[Math.floor(Math.random() * AGENTS.length)]
      )
      for (const a of movers) {
        setMoving(m => ({ ...m, [a.id]: true }))
        setWaypoint(prev => ({ ...prev, [a.id]: ((prev[a.id] ?? 0) + 1) % ZONES[a.id].length }))
        setTimeout(() => setMoving(m => ({ ...m, [a.id]: false })), 1400)
      }
    }, 1200)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    const t = setInterval(() => {
      setStatuses(prev => {
        const next = { ...prev }
        const a = AGENTS[Math.floor(Math.random()*AGENTS.length)]
        next[a.id] = STATUSES[Math.floor(Math.random()*STATUSES.length)]
        return next
      })
    }, 900)
    return () => clearInterval(t)
  }, [])

  // Cycle agent activities (eating, coffee, smoking, sleeping, etc.)
  useEffect(() => {
    const t = setInterval(() => {
      setActivities(prev => {
        const next = { ...prev }
        const a = AGENTS[Math.floor(Math.random() * AGENTS.length)]
        // 45% work, 55% random activity
        next[a.id] = Math.random() < 0.45
          ? "work"
          : ACTIVITIES[1 + Math.floor(Math.random() * (ACTIVITIES.length - 1))]
        return next
      })
    }, 3400)
    return () => clearInterval(t)
  }, [])

  // Win events → dance + UFO celebration + coin rain
  useEffect(() => {
    const onFx = (ev) => {
      const e = ev.detail
      if (e.type === "win" || e.type === "bigwin") {
        setDanceId(d => d + 1)
        setConfettiId(c => c + 1)
        setCelebrationId(c => c + 1)
        setTimeout(() => setDanceId(0), 4000)
      }
    }
    window.addEventListener("qwr:fx", onFx)
    return () => window.removeEventListener("qwr:fx", onFx)
  }, [])

  const lastSpeakerRef = useRef(activeId)
  useEffect(() => {
    if (lastSpeakerRef.current !== activeId) {
      lastSpeakerRef.current = activeId
      audio.speak()
    }
  }, [activeId])

  const dancing = danceId > 0

  const coord = (id) => {
    const zone = ZONES[id]
    const wp   = waypoint[id] ?? 0
    const [px, py] = zone[wp]
    const dx = Math.sin(drift * 0.6 + (id.charCodeAt(0)%7)) * 0.25
    const dy = Math.cos(drift * 0.5 + (id.charCodeAt(1)%7)) * 0.25
    return [ (px + dx) / 100 * size.w, (py + dy) / 100 * size.h ]
  }

  const activeAgent = AGENTS.find(a => a.id === activeId)

  return (
    <div
      ref={wrapRef}
      className="relative w-full qwr-panel overflow-hidden"
      style={{
        height: "min(62vh, 620px)",
        minHeight: 360,
        background: "linear-gradient(180deg, rgba(11,21,37,0.55) 0%, rgba(5,10,20,0.70) 100%)",
      }}
    >
      {/* Carpet tiles */}
      <div className="absolute inset-0 pointer-events-none" style={{
        backgroundImage: `
          linear-gradient(45deg, rgba(0,255,65,0.04) 25%, transparent 25%),
          linear-gradient(-45deg, rgba(204,68,255,0.04) 25%, transparent 25%),
          linear-gradient(45deg, transparent 75%, rgba(0,255,255,0.03) 75%),
          linear-gradient(-45deg, transparent 75%, rgba(255,255,0,0.03) 75%)
        `,
        backgroundSize: "24px 24px",
        backgroundPosition: "0 0, 0 12px, 12px -12px, -12px 0px",
        opacity: 0.5,
      }} />

      {/* Office props — desks attached to agents, scattered other items */}
      {/* ALPHA desk */}
      <WorkDesk x={12}  y={28} />
      {/* SKEPTIC desk */}
      <WorkDesk x={68}  y={24} />
      {/* EXECUTOR desk */}
      <WorkDesk x={40}  y={54} />
      {/* REGIME desk */}
      <WorkDesk x={14}  y={76} />
      {/* RISK desk */}
      <WorkDesk x={68}  y={66} />
      {/* RECOVERY desk */}
      <WorkDesk x={80}  y={52} />

      {/* ── Wall row (very top) ── */}
      <WindowView    x={15} y={4}  />
      <WallTV        x={35} y={4}  />
      <WallClock     x={50} y={4}  />
      <Poster        x={62} y={4}  text="HODL" color="#ffff00" />
      <WindowView    x={78} y={4}  />
      <Poster        x={92} y={4}  text="TRADE" color="#00ff41" />

      {/* ── Trader's pit: 3 trading desks with candlestick monitors ── */}
      <TradingDesk   x={22} y={26} />
      <TradingDesk   x={50} y={26} />
      <TradingDesk   x={78} y={26} />

      {/* ── Kitchen area (left) ── */}
      <KitchenUnit   x={16} y={52} />
      <Fridge        x={5}  y={52} />
      <Microwave     x={27} y={44} />

      {/* ── Pool / break zone (center) ── */}
      <PoolTable     x={50} y={52} />
      <Dartboard     x={36} y={42} />

      {/* ── Server wing (right) ── */}
      <ServerRack    x={95} y={40} />
      <ServerRack    x={95} y={78} />
      <FilingCabinet x={90} y={52} />

      {/* ── Misc accents ── */}
      <ArcadeMachine x={73} y={52} />
      <VendingMachine x={83} y={52} />
      <WaterCooler   x={66} y={46} />
      <Bookshelf     x={8}  y={80} />
      <Lockers       x={62} y={78} />
      <PingPongTable x={85} y={76} />
      <Printer       x={32} y={80} />


      {/* Grid + lines */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        <defs>
          <pattern id="arena-grid" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M 24 0 L 0 0 0 24" fill="none" stroke="rgba(26,48,80,0.3)" strokeWidth="1"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#arena-grid)" />

        {size.w > 1 && LINES.map(([a, b], i) => {
          const [x1, y1] = coord(a)
          const [x2, y2] = coord(b)
          const pulsing = pulseEdge && pulseEdge.idx === i
          const active  = a === activeId || b === activeId
          const colA = AGENTS.find(x => x.id === a)?.color
          const colB = AGENTS.find(x => x.id === b)?.color
          const col = dancing
            ? ["#00ff41","#ffff00","#ff5577","#00ffff"][i % 4]
            : (active ? (a === activeId ? colA : colB) : "rgba(74,112,144,0.35)")
          return (
            <g key={i}>
              <line
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={col}
                strokeWidth={pulsing || dancing ? 2 : active ? 1.5 : 1}
                strokeDasharray={pulsing ? "4 4" : active ? "6 6" : "2 6"}
                opacity={dancing ? 1 : pulsing ? 1 : active ? 0.85 : 0.3}
                style={{
                  animation: (pulsing || active || dancing) ? "qwr-flow 1.6s linear infinite" : undefined,
                  transition: "stroke 0.4s, stroke-width 0.4s",
                }}
              />
              {(active || dancing) && (
                <circle r={3} fill={col} style={{ filter: `drop-shadow(0 0 4px ${col})` }}>
                  <animateMotion dur={`${1.2 + (i % 3) * 0.35}s`} repeatCount="indefinite" path={`M ${x1} ${y1} L ${x2} ${y2}`} />
                </circle>
              )}
              {pulsing && (
                <circle r={5} fill="white" style={{ filter: `drop-shadow(0 0 8px ${col})` }}>
                  <animateMotion dur="0.8s" path={`M ${x1} ${y1} L ${x2} ${y2}`} />
                  <animate attributeName="opacity" values="1;0" dur="0.8s" fill="freeze" />
                </circle>
              )}
            </g>
          )
        })}
      </svg>

      {/* Party Club transformation */}
      <PartyClubMode active={dancing} />

      {/* Celebration UFO — hovers in middle, beam activates, coins rain */}
      <CelebrationUFO id={celebrationId} />
      <CoinRain       id={celebrationId} />

      {/* Confetti */}
      {confettiId > 0 && (
        <div key={confettiId} className="absolute inset-0">
          <Confetti burst={confettiId} />
        </div>
      )}

      {/* Agents — no frame, just characters walking/sitting */}
      {size.w > 1 && AGENTS.map((a, ai) => {
        const [x, y] = coord(a.id)
        const isActive = a.id === activeId
        const isMoving = moving[a.id]
        const atDesk   = (waypoint[a.id] ?? 0) === 0   // first waypoint = desk = sitting
        const conv = convictions?.[a.id] ?? 0.3
        const status = dancing ? "★ DANCE" : statuses[a.id]

        // Dance / walking / sitting animations
        const characterAnim =
          dancing
            ? { y: [0, -18, 0], rotate: [-14, 14, -14], scale: [1, 1.18, 1] }
            : isMoving
            ? { y: [0, -3, 0, -3, 0], rotate: [-3, 3, -3, 3, -3] }
            : atDesk
            ? { y: [0, -1, 0], rotate: 0 }
            : { y: [0, -2, 0], rotate: 0 }
        const characterTransition = {
          duration: dancing ? 0.5 : isMoving ? 0.5 : 2.4,
          repeat: Infinity,
          ease: "easeInOut",
          delay: dancing ? (ai * 0.07) : 0,
        }

        return (
          <button
            key={a.id}
            onClick={() => onSelectAgent?.(a.id)}
            className="absolute focus:outline-none"
            style={{
              left: x, top: y,
              transform: "translate(-50%, -50%)",
              transition: "left 1.6s cubic-bezier(0.45, 0, 0.2, 1), top 1.6s cubic-bezier(0.45, 0, 0.2, 1)",
              zIndex: isActive || dancing ? 5 : 2,
            }}
          >
            <div className="flex flex-col items-center gap-1">
              {/* Status chip */}
              <motion.div
                animate={dancing ? { y: [0, -6, 0], scale: [1, 1.15, 1] } : { y: [0, -1, 0] }}
                transition={{ duration: dancing ? 0.45 : 1.6, repeat: Infinity, ease: "easeInOut", delay: dancing ? ai * 0.05 : 0 }}
                className="pk text-[6px] px-1 py-[1px] border"
                style={{
                  color: dancing ? "#ffff00" : a.color,
                  borderColor: (dancing ? "#ffff00" : a.color) + (isActive || dancing ? "" : "55"),
                  background: (dancing ? "#ffff00" : a.color) + "15",
                  letterSpacing: 1.2,
                  boxShadow: (isActive || dancing) ? `0 0 6px ${dancing ? "#ffff00" : a.color}88` : undefined,
                }}
              >
                {status}
              </motion.div>

              {/* Character — no frame, just sprite + shadow */}
              <motion.div
                className="relative"
                animate={characterAnim}
                transition={characterTransition}
                style={{
                  filter:
                    dancing
                      ? `drop-shadow(0 0 12px ${a.color}) drop-shadow(0 0 20px ${a.color}88)`
                      : isActive
                      ? `drop-shadow(0 0 10px ${a.color}) drop-shadow(0 0 16px ${a.color}66)`
                      : `drop-shadow(0 2px 2px rgba(0,0,0,0.6))`,
                }}
              >
                <a.Sprite size={42} color={a.color} />

                {/* Activity emote floating above */}
                {!dancing && <ActivityEmote kind={activities[a.id]} />}

                {/* Walking motion lines behind */}
                {isMoving && !dancing && (
                  <>
                    <span
                      className="absolute top-1/2 -left-2 w-2 h-0.5"
                      style={{
                        background: a.color,
                        opacity: 0.6,
                        animation: "qwr-blink 0.2s infinite",
                      }}
                    />
                    <span
                      className="absolute top-1/3 -left-3 w-3 h-0.5"
                      style={{
                        background: a.color,
                        opacity: 0.3,
                      }}
                    />
                  </>
                )}

                {isActive && !dancing && (
                  <>
                    <motion.span
                      aria-hidden
                      className="absolute pointer-events-none"
                      style={{ left: "50%", top: "50%", marginLeft: -4, marginTop: -4 }}
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1.4, repeat: Infinity, ease: "linear" }}
                    >
                      <span
                        className="absolute w-1.5 h-1.5 rounded-full"
                        style={{ top: -30, left: 2, background: a.color, boxShadow: `0 0 6px ${a.color}` }}
                      />
                    </motion.span>
                  </>
                )}
              </motion.div>

              {/* Shadow beneath */}
              <div
                className="w-8 h-1 rounded-full -mt-1"
                style={{
                  background: "radial-gradient(ellipse, rgba(0,0,0,0.5), transparent)",
                  filter: "blur(2px)",
                }}
              />

              {/* Mini monitor */}
              <MiniMonitor color={a.color} active={isActive || dancing} />

              {/* Name */}
              <div
                className="pk text-[7px] tracking-widest mt-0.5"
                style={{
                  color: isActive || dancing ? a.color : "var(--subdim)",
                  textShadow: (isActive || dancing) ? `0 0 4px ${a.color}88` : undefined,
                }}
              >
                {a.name}
              </div>

              {/* Conviction bar */}
              <div className="h-1 w-12 border" style={{ borderColor: "var(--border)", background: "var(--panel)" }}>
                <div style={{
                  width: `${conv*100}%`, height: "100%", background: a.color,
                  boxShadow: `0 0 4px ${a.color}`, transition: "width 0.6s ease",
                }} />
              </div>
            </div>
          </button>
        )
      })}

      {/* DANCE banner */}
      <AnimatePresence>
        {dancing && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.6 }}
            animate={{ opacity: 1, y: 0,   scale: 1 }}
            exit={{    opacity: 0, y: -20, scale: 0.8 }}
            className="absolute top-4 left-1/2 -translate-x-1/2 pk text-[14px] px-3 py-2 border pointer-events-none z-10"
            style={{
              color: "#ffff00", borderColor: "#ffff00",
              background: "rgba(255,255,0,0.08)",
              boxShadow: "0 0 24px rgba(255,255,0,0.55)",
              textShadow: "0 0 8px rgba(255,255,0,0.9)",
              letterSpacing: 4,
            }}
          >
            ♪ ♪   WIN · PARTY MODE   ♪ ♪
          </motion.div>
        )}
      </AnimatePresence>

      {/* Corner labels */}
      <div className="absolute top-2 left-3 pk text-[8px] text-[color:var(--green)] tracking-widest" style={{ animation: "qwr-flicker 4s infinite" }}>
        ● AGENT OFFICE
      </div>
      <div className="absolute top-2 right-3 pk text-[7px] text-[color:var(--subdim)] tracking-widest">
        {LINES.length} LINKS · {AGENTS.length} STAFF
      </div>
      <div className="absolute bottom-2 left-3 pk text-[7px] text-[color:var(--subdim)] tracking-widest">
        OPEN PLAN · FLOOR 42
      </div>
      <div className="absolute bottom-2 right-3 pk text-[8px] tracking-widest flex items-center gap-2" style={{ color: activeAgent?.color }}>
        <span className="inline-block w-2 h-2" style={{ background: activeAgent?.color, boxShadow: `0 0 6px ${activeAgent?.color}`, animation: "qwr-blink 0.8s infinite" }} />
        SPEAKER: {(activeId||"").toUpperCase()}
      </div>
    </div>
  )
}
