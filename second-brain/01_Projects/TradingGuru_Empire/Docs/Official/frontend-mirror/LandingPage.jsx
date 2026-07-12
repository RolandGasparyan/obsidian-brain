import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { audio } from "../ui/audio_engine.js"
import LoginModal, { getSession } from "../components/LoginModal.jsx"
import {
  useTerminalData,
  selectEquity,
  selectAgents,
  selectHalted,
} from "../lib/useTerminalData.js"

// ── Live status helpers — derive truthful arena status from terminal.json ──
function deriveArenaStatus(data) {
  if (!data) return { label: "◯ CONNECTING TO ARENA…", color: "var(--subdim)" }
  const halted   = Boolean(data?.protection?.global_halt?.halted) || Boolean(data?.session?.halted)
  const safeMode = Boolean(data?.protection?.safe_mode?.active)
  const alive    = Boolean(data?.bot?.alive)
  if (halted)   return { label: "◣ ARENA HALTED · CAPITAL PROTECTION ENGAGED ◢", color: "var(--accent-pink)" }
  if (!alive)   return { label: "◯ ARENA STANDBY · NEXT ROUND PENDING ◯",       color: "var(--accent-orange)" }
  if (safeMode) return { label: "◆ ARENA LIVE · SAFE MODE · MEASURED EXECUTION ◆", color: "var(--accent-yellow)" }
  return         { label: "▶ ARENA LIVE · AGENTS ENGAGED · ROUNDS ACTIVE ◀",       color: "var(--accent-green)" }
}

function formatRelative(d) {
  if (!d) return "—"
  const s = Math.floor((Date.now() - d.getTime()) / 1000)
  if (s < 5)   return "JUST NOW"
  if (s < 60)  return `${s}s AGO`
  if (s < 3600) return `${Math.floor(s/60)}m AGO`
  return `${Math.floor(s/3600)}h AGO`
}

// Reuse UFO logo design from intro (inline for self-containment)
function UfoLogo({ size = 200, tick = 0 }) {
  const W = 26, H = 16
  const px = (a, b, w = 1, h = 1, c) => (
    <rect key={`${a}-${b}-${c}-${w}-${h}`} x={a} y={b} width={w} height={h} fill={c} />
  )
  const body = "#00ddcc", bodyLo = "#0a8a85", dome = "#88ff00", lights = "var(--accent-yellow)"
  const eyeOpen = tick % 10 !== 0
  return (
    <svg
      width={size}
      height={size * (H / W)}
      viewBox={`0 0 ${W} ${H}`}
      style={{
        imageRendering: "pixelated",
        filter: "drop-shadow(0 0 20px rgba(0,255,200,0.6)) drop-shadow(0 0 40px rgba(0,255,65,0.4))",
      }}
    >
      {px(12, 0, 2, 1, "var(--border)")}
      {px(10, 1, 6, 1, dome)}
      {px( 9, 2, 8, 1, dome)}
      {px( 9, 3, 8, 1, dome)}
      {px(10, 2, 2, 1, "#b8ff55")}
      {px(10, 1, 1, 1, "#ffffff")}
      {px(11, 2, 4, 1, "#88ff00")}
      {px(10, 3, 6, 1, "#88ff00")}
      {eyeOpen
        ? <>{px(11, 3, 1, 1, "var(--border)")}{px(14, 3, 1, 1, "var(--border)")}</>
        : <>{px(11, 3.3, 1, 0.4, "var(--border)")}{px(14, 3.3, 1, 0.4, "var(--border)")}</>
      }
      {px( 6, 4, 14, 1, "#5df5e6")}
      {px( 4, 5,  1, 1, body)}
      {px( 5, 5,  1, 1, lights)}
      {px( 6, 5,  2, 1, body)}
      {px( 8, 5,  1, 1, "var(--accent-pink)")}
      {px( 9, 5,  2, 1, body)}
      {px(11, 5,  1, 1, lights)}
      {px(12, 5,  2, 1, body)}
      {px(14, 5,  1, 1, "var(--accent-pink)")}
      {px(15, 5,  2, 1, body)}
      {px(17, 5,  1, 1, lights)}
      {px(18, 5,  2, 1, body)}
      {px(20, 5,  1, 1, "#5df5e6")}
      {px( 2, 6, 22, 1, body)}
      {px( 1, 7, 24, 1, "var(--border)")}
      {px( 2, 7, 22, 1, body)}
      {px( 4, 8,  1, 1, "#ff00ff")}
      {px( 5, 8, 16, 1, bodyLo)}
      {px(21, 8,  1, 1, "var(--accent-cyan)")}
      {px( 7, 9, 12, 1, bodyLo)}
      {px( 9,10,  8, 1, bodyLo)}
      {px(11,11,  4, 1, bodyLo)}
      {px(12,12,  2, 1, "#ffffff")}
    </svg>
  )
}

// Reusable rule card with hover lift + colored glow
// AgentLeaderCard — top-3 agent tile, ranked by sharpe.
// Renders only real fields from terminal.json; absent fields show "—".
function AgentLeaderCard({ agent, rank }) {
  const rankColor = rank === 1 ? "var(--accent-yellow)" : rank === 2 ? "var(--accent-cyan)" : "var(--accent-purple)"
  const rankIcon  = rank === 1 ? "★" : rank === 2 ? "◆" : "▲"
  const sharpe = Number(agent?.sharpe ?? 0)
  const pnl    = Number(agent?.pnl ?? 0)
  const wr     = Number(agent?.win_rate ?? 0)
  const trades = Number(agent?.trades ?? 0)
  const disabled = Boolean(agent?.disabled)
  return (
    <motion.div
      className="qwr-panel p-3 relative overflow-hidden"
      whileHover={{ scale: 1.025, y: -2 }}
      transition={{ type: "spring", stiffness: 360, damping: 24 }}
      style={{
        background: "rgba(8,15,30,0.6)",
        borderColor: `${rankColor}55`,
        boxShadow: `0 0 16px -8px ${rankColor}77, inset 0 0 10px ${rankColor}11`,
        opacity: disabled ? 0.55 : 1,
      }}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span
          className="pk text-[10px] tracking-widest"
          style={{ color: rankColor, textShadow: `0 0 6px ${rankColor}88` }}
        >
          {rankIcon} #{rank}
        </span>
        <span
          className="pk text-[9px] tracking-widest"
          style={{ color: "var(--subdim)" }}
        >
          {disabled ? "DISABLED" : "ACTIVE"}
        </span>
      </div>
      <div
        className="pk truncate"
        style={{
          color: "#fff",
          fontSize: "clamp(0.85rem, 1.3vw + 0.3rem, 1rem)",
          letterSpacing: "0.05em",
          textShadow: `0 0 6px ${rankColor}55`,
        }}
      >
        {agent?.label || `AGENT ${agent?.id ?? "—"}`}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1.5 text-[9px] mono">
        <div>
          <span style={{ color: "var(--subdim)" }}>SHARPE</span>
          <div style={{ color: sharpe >= 0 ? "var(--accent-green)" : "var(--accent-pink)" }}>
            {sharpe.toFixed(2)}
          </div>
        </div>
        <div>
          <span style={{ color: "var(--subdim)" }}>PNL</span>
          <div style={{ color: pnl >= 0 ? "var(--accent-green)" : "var(--accent-pink)" }}>
            {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
          </div>
        </div>
        <div>
          <span style={{ color: "var(--subdim)" }}>WR</span>
          <div style={{ color: "var(--accent-cyan)" }}>{(wr * 100).toFixed(1)}%</div>
        </div>
        <div>
          <span style={{ color: "var(--subdim)" }}>TRADES</span>
          <div style={{ color: "var(--accent-orange)" }}>{trades}</div>
        </div>
      </div>
    </motion.div>
  )
}

// LiveCell — honest live-data tile. Shows "—" when loading, value when ready,
// "OFFLINE" when fetch fails. No mock fallbacks, no Math.random().
function LiveCell({ label, value, color, loading }) {
  return (
    <motion.div
      className="qwr-panel px-3 py-2.5 md:px-4 md:py-3 relative overflow-hidden"
      style={{
        background: "rgba(8,15,30,0.55)",
        borderColor: `${color}55`,
        boxShadow: `0 0 14px -6px ${color}55, inset 0 0 8px ${color}11`,
      }}
      whileHover={{ scale: 1.02 }}
      transition={{ type: "spring", stiffness: 380, damping: 26 }}
    >
      <div
        className="pk text-[8px] tracking-widest"
        style={{ color: "var(--subdim)" }}
      >
        ◆ {label}
      </div>
      <div
        className="pk mt-1.5 truncate"
        style={{
          color,
          fontSize: "clamp(0.8rem, 1.4vw + 0.3rem, 1.05rem)",
          textShadow: `0 0 8px ${color}88`,
          letterSpacing: "0.04em",
        }}
      >
        {loading ? (
          <motion.span
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.4, repeat: Infinity }}
          >…</motion.span>
        ) : value}
      </div>
    </motion.div>
  )
}

function RuleCard({ num, title, desc, color }) {
  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
      className="qwr-panel p-5 cursor-default"
      style={{ boxShadow: `0 0 0 1px ${color}33, 0 0 30px -10px ${color}66` }}
    >
      <div className="flex items-baseline gap-3 mb-3">
        <div
          className="pk text-2xl"
          style={{ color, textShadow: `0 0 10px ${color}aa` }}
        >
          {num}
        </div>
        <div
          className="pk text-[10px] tracking-widest"
          style={{ color }}
        >
          {title}
        </div>
      </div>
      <div className="text-sm text-[color:var(--text)] leading-relaxed mono">
        {desc}
      </div>
    </motion.div>
  )
}

// Subscription pricing tile — 2026-05-12 sized for balance: smaller price
// number, tighter padding, fluid typography, no excessive empty space.
function PriceTile({ tag, period, price, perks, color, popular = false }) {
  return (
    <motion.div
      whileHover={{ y: -5, scale: 1.025 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
      className="qwr-panel p-5 md:p-6 relative flex flex-col"
      style={{
        boxShadow: popular
          ? `0 0 0 2px ${color}, 0 0 36px -10px ${color}cc`
          : `0 0 0 1px ${color}33, 0 0 22px -8px ${color}66`,
        background: popular
          ? `linear-gradient(180deg, ${color}11, transparent 60%)`
          : undefined,
        borderRadius: 4,
      }}
    >
      {popular && (
        <motion.div
          animate={{ opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -top-3 left-1/2 -translate-x-1/2 pk text-[8px] tracking-widest px-2 py-1 whitespace-nowrap"
          style={{
            color: "#0a0e1a",
            background: color,
            boxShadow: `0 0 14px ${color}cc`,
            borderRadius: 2,
          }}
        >
          ★ MOST POPULAR
        </motion.div>
      )}

      <div className="pk text-[10px] tracking-widest mb-2"
           style={{ color, textShadow: `0 0 8px ${color}80` }}>
        {tag}
      </div>

      <div className="flex items-baseline gap-2 mb-0.5">
        <div
          className="pk leading-none"
          style={{
            color: "#fff",
            textShadow: `0 0 14px ${color}aa`,
            fontSize: "clamp(2.25rem, 4vw + 0.5rem, 3.25rem)",
          }}
        >
          {price}
        </div>
        <div className="pk text-[10px] tracking-widest text-[color:var(--subdim)]">
          USDT
        </div>
      </div>

      <div className="pk text-[9px] tracking-widest text-[color:var(--subdim)] mb-4">
        / {period}
      </div>

      <ul className="text-[12px] mono space-y-1 text-[color:var(--text)] mb-4 flex-1">
        {perks.map((p, i) => (
          <li key={i}><span style={{color}}>►</span> {p}</li>
        ))}
      </ul>

      <motion.button
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.96 }}
        className="pk w-full text-xs px-4 py-3 border-2 tracking-widest min-h-touch"
        style={{
          color, borderColor: color,
          background: `${color}14`,
          boxShadow: `0 0 12px -3px ${color}99`,
          borderRadius: 4,
        }}
      >
        ◆ SUBSCRIBE
      </motion.button>
    </motion.div>
  )
}

export default function LandingPage() {
  const [tick, setTick] = useState(0)
  const [loginOpen, setLoginOpen] = useState(false)
  const [session, setSession] = useState(() => getSession())
  // Live data from /api/battle/terminal.json — polled every 60s
  const { data: liveData, lastUpdated, error: liveError } = useTerminalData()
  const arenaStatus = deriveArenaStatus(liveData)
  const liveEquity  = liveData ? selectEquity(liveData) : null
  const liveAgents  = liveData ? selectAgents(liveData) : []
  const activeAgents = liveAgents.filter(a => !a.disabled).length
  const liveHalted  = liveData ? selectHalted(liveData) : null

  useEffect(() => {
    const t = setInterval(() => setTick(v => v + 1), 220)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    const onSession = (e) => setSession(e.detail)
    window.addEventListener("qwr:session", onSession)
    return () => window.removeEventListener("qwr:session", onSession)
  }, [])

  return (
    <div className="relative min-h-screen qwr-crt">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 0.61, 0.36, 1] }}
        className="relative z-10 max-w-[1400px] mx-auto px-4 md:px-8 pt-20 pb-16 space-y-16"
      >
        {/* ── HERO ── */}
        <section className="text-center space-y-8">
          <motion.div
            className="flex justify-center"
            animate={{ y: [0, -6, 0], rotate: [-1.5, 1.5, -1.5] }}
            transition={{ duration: 3.8, repeat: Infinity, ease: "easeInOut" }}
          >
            <UfoLogo size={200} tick={tick} />
          </motion.div>

          <div className="space-y-3">
            {/* TRADING GURU wordmark removed 2026-05-11 per EXECUTE_PURGE_TRADING_GURU */}
            <div
              className="pk text-3xl md:text-5xl text-[color:var(--green)] whitespace-nowrap"
              style={{ textShadow: "0 0 24px rgba(0,255,65,0.85), 0 0 48px rgba(0,255,65,0.5), 0 0 80px rgba(0,255,200,0.3)" }}
            >
              AI TRADING CHAMPIONSHIP
            </div>
            <div className="pk text-[10px] tracking-widest text-[color:var(--cyan)] mt-4">
              ◆ THE FIRST 24/7 AI-VS-AI TRADING ARENA · BET · PREDICT · BUILD ◆
            </div>
          </div>

          {/* CTAs */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
            {/* Phase 13: prominent racing CTA — 8-agent paper race showcase */}
            <Link to="/racing" onClick={() => audio.click()}>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                animate={{
                  boxShadow: [
                    "0 0 20px rgba(255,215,0,0.4)",
                    "0 0 32px rgba(255,215,0,0.7)",
                    "0 0 20px rgba(255,215,0,0.4)",
                  ],
                }}
                transition={{ duration: 2.4, repeat: Infinity }}
                className="pk text-sm px-8 py-4 border tracking-widest"
                style={{
                  color: "var(--accent-yellow)",
                  borderColor: "var(--accent-yellow)",
                  background: "rgba(255,215,0,0.10)",
                  textShadow: "0 0 8px rgba(255,215,0,0.8)",
                }}
              >
                🏁 WATCH THE PAPER RACE
              </motion.button>
            </Link>
            <Link to="/arena" onClick={() => audio.click()}>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="pk text-sm px-8 py-4 border tracking-widest"
                style={{
                  color: "var(--accent-green)",
                  borderColor: "var(--accent-green)",
                  background: "rgba(0,255,65,0.08)",
                  boxShadow: "0 0 20px rgba(0,255,65,0.4)",
                  textShadow: "0 0 8px rgba(0,255,65,0.8)",
                }}
              >
                ► ENTER ARENA
              </motion.button>
            </Link>
            {!session ? (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => { audio.click?.(); setLoginOpen(true) }}
                className="pk text-sm px-8 py-4 border tracking-widest"
                style={{
                  color: "var(--accent-yellow)",
                  borderColor: "var(--accent-yellow)",
                  background: "rgba(255,255,0,0.08)",
                  boxShadow: "0 0 20px rgba(255,255,0,0.4)",
                  textShadow: "0 0 8px rgba(255,255,0,0.8)",
                }}
              >
                ★ LOG IN / SIGN UP
              </motion.button>
            ) : (
              <Link to="/dashboard" onClick={() => audio.click()}>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="pk text-sm px-8 py-4 border tracking-widest"
                  style={{
                    color: "var(--accent-yellow)",
                    borderColor: "var(--accent-yellow)",
                    background: "rgba(255,255,0,0.08)",
                    boxShadow: "0 0 20px rgba(255,255,0,0.4)",
                  }}
                >
                  ► OPEN ACCOUNT
                </motion.button>
              </Link>
            )}
          </div>
        </section>

        {/* ── THE FIRST AI TRADING CHALLENGE — INTRO ── */}
        <section className="qwr-panel p-6 md:p-10 relative overflow-hidden">
          <div
            aria-hidden
            className="absolute inset-0 pointer-events-none opacity-40"
            style={{
              background:
                "radial-gradient(circle at 80% 0%, rgba(255,255,0,0.10), transparent 55%), radial-gradient(circle at 20% 100%, rgba(0,255,200,0.08), transparent 55%)",
            }}
          />
          <div className="relative z-10 grid grid-cols-1 md:grid-cols-[1.25fr_1fr] gap-8 items-center">
            <div className="space-y-5">
              <motion.div
                animate={{ opacity: [0.8, 1, 0.8] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                className="pk text-[10px] tracking-widest"
                style={{ color: "var(--accent-yellow)", textShadow: "0 0 8px rgba(255,255,0,0.6)" }}
              >
                ★ THE FIRST AI TRADING CHALLENGE
              </motion.div>
              <div
                className="pk leading-tight"
                style={{
                  color: "var(--accent-green)",
                  textShadow:
                    "0 0 16px rgba(0,255,65,0.7), 0 0 32px rgba(0,255,65,0.35)",
                  fontSize: "clamp(1.4rem, 3.4vw + 0.4rem, 2.4rem)",
                }}
              >
                <span className="whitespace-nowrap">AI AGENTS BATTLE.</span><br/>
                <span className="whitespace-nowrap">YOU BET. YOU EARN.</span>
              </div>
              <p className="text-sm md:text-base text-[color:var(--text)] mono leading-relaxed max-w-[60ch]">
                Trading Guru is the first <b style={{color:"var(--accent-green)"}}>24/7 live arena</b> where
                autonomous AI trading agents compete head-to-head on real markets. Each round, the
                agent that <b style={{color:"var(--accent-yellow)"}}>captures the most profit wins the pot</b>.
                Spectators bet on agents, predict market moves, and earn rewards. Developers can
                register their own agents and challenge the meta.
              </p>
              <ul className="text-[13px] mono space-y-1.5 text-[color:var(--text)]">
                <li><span style={{color:"var(--accent-green)"}}>►</span> Live, transparent, on-chain trade tape</li>
                <li><span style={{color:"var(--accent-cyan)"}}>►</span> Max-profit-wins-the-round battle format</li>
                <li><span style={{color:"#ff9b3d"}}>►</span> Bet on agents · predict markets · stack wins</li>
                <li><span style={{color:"var(--accent-yellow)"}}>►</span> Open developer SDK — bring your own AI</li>
              </ul>
            </div>

            {/* 6-stat grid replaced 2026-05-11 per EXECUTE_REPLACE_WITH_WAITLIST.
                Sized 2026-05-11-v2: balanced proportions vs. hero text on right. */}
            <div className="flex justify-center md:justify-start">
              <Link to="/" onClick={() => audio.click?.()} className="block w-full max-w-[420px]">
                <motion.button
                  whileHover={{ scale: 1.04, y: -3 }}
                  whileTap={{ scale: 0.97 }}
                  animate={{
                    boxShadow: [
                      "0 0 20px rgba(0,255,65,0.4), inset 0 0 12px rgba(0,255,65,0.1)",
                      "0 0 36px rgba(0,255,65,0.85), inset 0 0 22px rgba(0,255,65,0.28)",
                      "0 0 20px rgba(0,255,65,0.4), inset 0 0 12px rgba(0,255,65,0.1)",
                    ],
                  }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
                  className="pk w-full tracking-[0.30em] px-5 py-4 md:py-5 border-2 min-h-touch relative overflow-hidden flex flex-col items-center justify-center gap-1.5"
                  style={{
                    color: "var(--accent-green)",
                    borderColor: "var(--accent-green)",
                    background: "linear-gradient(135deg, rgba(0,255,65,0.18), rgba(0,255,65,0.04), rgba(0,255,65,0.12))",
                    textShadow: "0 0 12px rgba(0,255,65,0.9), 0 0 24px rgba(0,255,65,0.45)",
                    borderRadius: 4,
                    fontSize: "clamp(0.95rem, 1.8vw + 0.35rem, 1.25rem)",
                  }}
                >
                  {/* holographic shimmer sweep */}
                  <motion.span
                    aria-hidden
                    animate={{ x: ["-160%", "220%"] }}
                    transition={{ duration: 2.6, repeat: Infinity, ease: "linear" }}
                    style={{
                      position: "absolute", inset: 0,
                      background: "linear-gradient(110deg, transparent 35%, rgba(0,255,65,0.4) 50%, transparent 65%)",
                      pointerEvents: "none",
                      mixBlendMode: "screen",
                    }}
                  />

                  <span style={{ position: "relative", zIndex: 2, lineHeight: 1.1 }}>
                    <motion.span
                      animate={{ rotate: [0, 12, -12, 0] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      style={{ display: "inline-block", marginRight: 7 }}
                    >★</motion.span>
                    JOIN WAITLIST
                  </span>

                  <span
                    className="pk tracking-widest whitespace-nowrap"
                    style={{
                      position: "relative", zIndex: 2,
                      color: "rgba(0,255,255,0.82)",
                      fontSize: "clamp(0.5rem, 0.7vw + 0.28rem, 0.65rem)",
                      textShadow: "0 0 5px rgba(0,255,255,0.55)",
                      letterSpacing: "0.22em",
                    }}
                  >
                    ◆ BE AMONG THE FIRST 1,000 ◆
                  </span>
                </motion.button>
              </Link>
            </div>
          </div>

          {/* ── LIVE DATA STRIP — honest backend feed, no fake numbers ──
              Added 2026-05-12 per EXPAND_TO_LANDING_TOO.
              Pulls from /api/battle/terminal.json (60s poll). */}
          <div
            className="relative z-10 mt-8 pt-6 grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4"
            style={{ borderTop: "1px dashed var(--border)" }}
          >
            <LiveCell
              label="ARENA EQUITY"
              value={liveData
                ? `$${liveEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                : "—"}
              color="var(--accent-green)"
              loading={!liveData && !liveError}
            />
            <LiveCell
              label="ACTIVE AGENTS"
              value={liveData ? `${activeAgents} / ${liveAgents.length}` : "—"}
              color="var(--accent-cyan)"
              loading={!liveData && !liveError}
            />
            <LiveCell
              label="STATUS"
              value={liveData
                ? (liveHalted ? "HALTED" : (liveData?.protection?.safe_mode?.active ? "SAFE MODE" : "LIVE"))
                : "—"}
              color={arenaStatus.color}
              loading={!liveData && !liveError}
            />
            <LiveCell
              label="LAST UPDATE"
              value={liveError ? "OFFLINE" : formatRelative(lastUpdated)}
              color={liveError ? "var(--accent-pink)" : "var(--accent-yellow)"}
              loading={!liveData && !liveError}
            />
          </div>

          {/* ── TOP AGENTS LIVE — top 3 by sharpe, real data ──
              Added 2026-05-12 per EXPAND_TO_LANDING_REAL. */}
          {liveData && liveAgents.length > 0 && (
            <div className="relative z-10 mt-6">
              <div
                className="pk text-[9px] tracking-widest mb-3 text-center"
                style={{ color: "var(--subdim)" }}
              >
                ◆ TOP AGENTS RIGHT NOW · LIVE FROM ARENA ◆
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[...liveAgents]
                  .sort((a, b) => (b.sharpe || 0) - (a.sharpe || 0) || (b.pnl || 0) - (a.pnl || 0))
                  .slice(0, 3)
                  .map((agent, idx) => (
                    <AgentLeaderCard key={agent.id ?? idx} agent={agent} rank={idx + 1} />
                  ))}
              </div>
            </div>
          )}

          {/* ── PAIRS COVERED — live ticker of symbols the arena trades ── */}
          {liveData?.pairs?.length > 0 && (
            <div className="relative z-10 mt-5">
              <div
                className="pk text-[8px] tracking-widest mb-2 text-center"
                style={{ color: "var(--subdim)" }}
              >
                ◆ PAIRS COVERED ◆
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {liveData.pairs.slice(0, 12).map((p) => (
                  <span
                    key={p}
                    className="pk text-[9px] tracking-widest px-2 py-1 border"
                    style={{
                      color: "var(--accent-cyan)",
                      borderColor: "rgba(0,255,255,0.35)",
                      background: "rgba(0,255,255,0.05)",
                      textShadow: "0 0 6px rgba(0,255,255,0.55)",
                    }}
                  >
                    {p.replace("/", "·")}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* ── HOW THE BATTLE WORKS ── */}
        <section>
          <h2
            className="pk text-lg md:text-xl text-center mb-8 tracking-widest"
            style={{ color: "var(--accent-green)", textShadow: "0 0 12px rgba(0,255,65,0.6)" }}
          >
            ► HOW THE BATTLE WORKS
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <RuleCard
              num="01"
              color="var(--accent-green)"
              title="ROUND BATTLE FORMAT"
              desc="Every round, AI agents start with the same capital and trade live markets. The agent with the highest realized PnL at round-end takes the pot. Pure performance, no luck."
            />
            <RuleCard
              num="02"
              color="var(--accent-cyan)"
              title="24/7 NON-STOP"
              desc="Markets never sleep — neither do the agents. Battles run continuously across multiple pairs. New rounds spin up automatically; results post in real time."
            />
            <RuleCard
              num="03"
              color="#ff9b3d"
              title="MAX PROFIT WINS"
              desc="One rule. Highest end-of-round profit takes the round. Tie-break by Sharpe ratio, then by max single-trade R-multiple. Transparent scoring on the leaderboard."
            />
            <RuleCard
              num="04"
              color="var(--accent-purple)"
              title="BET ON AGENTS"
              desc="Pick your champion before the round locks. Stake USDT on which agent will win the round. Pari-mutuel pool — bigger, smarter pools split the rewards proportionally."
            />
            <RuleCard
              num="05"
              color="var(--accent-pink)"
              title="MARKET PREDICTIONS"
              desc="Beyond agent bets — predict where BTC, ETH, SOL close. Binary up/down or range bets with payout multipliers. Compete on the prediction leaderboard for streak rewards."
            />
            <RuleCard
              num="06"
              color="var(--accent-yellow)"
              title="DEVELOPERS WELCOME"
              desc="Register your own AI trading agent through our SDK. Pass the qualifier, enter the open division, climb to the championship. Royalty share when your agent gets bet on."
            />
          </div>
        </section>

        {/* ── BET ON AGENTS + MARKET PREDICTIONS ── */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="qwr-panel p-6 md:p-8 relative overflow-hidden"
            style={{ boxShadow: "0 0 0 1px rgba(204,68,255,0.25), 0 0 28px -8px rgba(204,68,255,0.5)" }}
          >
            <div
              aria-hidden
              className="absolute inset-0 opacity-50 pointer-events-none"
              style={{
                background: "radial-gradient(circle at 100% 0%, rgba(204,68,255,0.16), transparent 55%)",
              }}
            />
            <div className="relative z-10 space-y-4">
              <div className="pk text-[10px] tracking-widest" style={{ color: "var(--accent-purple)" }}>
                ◆ AGENT BETS
              </div>
              <div className="pk text-xl md:text-2xl" style={{ color: "#fff", textShadow: "0 0 14px rgba(204,68,255,0.55)" }}>
                BACK YOUR CHAMPION
              </div>
              <p className="text-sm mono text-[color:var(--text)] leading-relaxed">
                Place USDT on the agent you think will dominate the round. Pools open at round-start
                and lock 60s before settlement. Winners split the pool proportional to their stake —
                no house edge, just sharper bettors taking the soft money.
              </p>
              <ul className="text-[12px] mono space-y-1 text-[color:var(--text)]">
                <li><span style={{color:"var(--accent-purple)"}}>•</span> Pari-mutuel pool (peer-vs-peer)</li>
                <li><span style={{color:"var(--accent-purple)"}}>•</span> Min stake 1 USDT · Max stake 10K USDT</li>
                <li><span style={{color:"var(--accent-purple)"}}>•</span> Stack wins for streak bonuses up to +25%</li>
              </ul>
            </div>
          </motion.div>

          <motion.div
            whileHover={{ scale: 1.01 }}
            className="qwr-panel p-6 md:p-8 relative overflow-hidden"
            style={{ boxShadow: "0 0 0 1px rgba(255,85,119,0.25), 0 0 28px -8px rgba(255,85,119,0.5)" }}
          >
            <div
              aria-hidden
              className="absolute inset-0 opacity-50 pointer-events-none"
              style={{
                background: "radial-gradient(circle at 0% 100%, rgba(255,85,119,0.16), transparent 55%)",
              }}
            />
            <div className="relative z-10 space-y-4">
              <div className="pk text-[10px] tracking-widest" style={{ color: "var(--accent-pink)" }}>
                ◇ MARKET PREDICTIONS
              </div>
              <div className="pk text-xl md:text-2xl" style={{ color: "#fff", textShadow: "0 0 14px rgba(255,85,119,0.55)" }}>
                CALL THE MARKET
              </div>
              <p className="text-sm mono text-[color:var(--text)] leading-relaxed">
                Forecast where BTC, ETH, SOL close in 5m / 1h / 24h windows. Binary up/down,
                range bets, or precision targets. Multipliers scale with difficulty. Build a streak,
                climb the prediction ladder, earn weekly leaderboard rewards.
              </p>
              <ul className="text-[12px] mono space-y-1 text-[color:var(--text)]">
                <li><span style={{color:"var(--accent-pink)"}}>•</span> Binary, range &amp; precision modes</li>
                <li><span style={{color:"var(--accent-pink)"}}>•</span> 5m / 1h / 24h windows</li>
                <li><span style={{color:"var(--accent-pink)"}}>•</span> Streak multipliers up to 5×</li>
              </ul>
            </div>
          </motion.div>
        </section>

        {/* ── FOR DEVELOPERS ── */}
        <section className="qwr-panel p-6 md:p-10 relative overflow-hidden">
          <div
            aria-hidden
            className="absolute inset-0 opacity-50 pointer-events-none"
            style={{
              background:
                "radial-gradient(circle at 50% 0%, rgba(255,255,0,0.12), transparent 60%)",
            }}
          />
          <div className="relative z-10 grid grid-cols-1 md:grid-cols-[1fr_1.2fr] gap-8 items-center">
            <div className="space-y-4">
              <div className="pk text-[10px] tracking-widest" style={{ color: "var(--accent-yellow)" }}>
                ⚡ FOR DEVELOPERS
              </div>
              <div className="pk text-xl md:text-3xl leading-tight" style={{
                color: "#fff",
                textShadow: "0 0 14px rgba(255,255,0,0.55)",
              }}>
                BUILD YOUR AGENT.<br/>BREAK THE META.
              </div>
              <p className="text-sm mono text-[color:var(--text)] leading-relaxed">
                Register your own AI trading agent through the public SDK. Pass the qualifier
                round, enter the open division, climb to the championship arena. When your agent
                gets bet on, you earn a share of the pool fees. Push the meta — the hardest agent
                wins the most attention.
              </p>
            </div>
            <ul className="text-[13px] mono space-y-2 text-[color:var(--text)]">
              <li><span style={{color:"var(--accent-yellow)"}}>►</span> SDK in Python &amp; TypeScript · websocket order routing</li>
              <li><span style={{color:"var(--accent-yellow)"}}>►</span> Backtest sandbox · live paper round before promotion</li>
              <li><span style={{color:"var(--accent-yellow)"}}>►</span> Qualifier → Open → Pro → Championship divisions</li>
              <li><span style={{color:"var(--accent-yellow)"}}>►</span> Royalty share on bets placed on your agent</li>
              <li><span style={{color:"var(--accent-yellow)"}}>►</span> Open leaderboard · public R-curve · public source optional</li>
            </ul>
          </div>
        </section>

        {/* ── SUBSCRIPTION ── */}
        <section>
          <h2
            className="pk text-lg md:text-xl text-center mb-3 tracking-widest"
            style={{ color: "var(--accent-yellow)", textShadow: "0 0 12px rgba(255,255,0,0.55)" }}
          >
            ★ SUBSCRIPTION TIERS
          </h2>
          <div className="pk text-[9px] text-center tracking-widest text-[color:var(--subdim)] mb-8">
            UNLOCK FULL ACCESS · BET · PREDICT · BUILD
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-[860px] mx-auto">
            <PriceTile
              tag="◆ DAILY PASS"
              period="day"
              price="1"
              color="var(--accent-cyan)"
              perks={[
                "Full account access",
                "Bet on agents · place predictions",
                "Live trade tape · all pairs",
                "Cancel anytime — no commitment",
              ]}
            />
            <PriceTile
              tag="★ MONTHLY PRO"
              period="month"
              price="33"
              color="var(--accent-yellow)"
              popular
              perks={[
                "Everything in Daily Pass",
                "Developer SDK access · register agents",
                "Priority match queue · advanced bet types",
                "33% cheaper than 30 daily passes",
              ]}
            />
          </div>
          <div className="text-center mt-6">
            <span className="pk text-[8px] tracking-widest text-[color:var(--subdim)]">
              ◄ ALL PAYMENTS IN USDT · INSTANT ACTIVATION ►
            </span>
          </div>
        </section>

        {/* ── FINAL CTA ── */}
        <section className="qwr-panel p-8 text-center space-y-4 relative overflow-hidden">
          <div
            aria-hidden
            className="absolute inset-0 opacity-50 pointer-events-none"
            style={{
              background:
                "radial-gradient(circle at 50% 100%, rgba(0,255,65,0.18), transparent 55%)",
            }}
          />
          <div className="relative z-10 space-y-4">
            <motion.div
              className="pk text-[10px] tracking-widest"
              style={{
                color: arenaStatus.color,
                textShadow: `0 0 8px ${arenaStatus.color}55`,
              }}
              animate={{ opacity: [0.65, 1, 0.65] }}
              transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
            >
              {arenaStatus.label}
            </motion.div>
            <div
              className="pk text-lg md:text-2xl text-[color:var(--green)]"
              style={{ textShadow: "0 0 14px rgba(0,255,65,0.7)" }}
            >
              READY TO ENTER THE BATTLE?
            </div>
            <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
              {!session && (
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  onClick={() => { audio.click?.(); setLoginOpen(true) }}
                  className="pk text-xs px-6 py-3 border tracking-widest"
                  style={{
                    color: "var(--accent-yellow)",
                    borderColor: "var(--accent-yellow)",
                    background: "rgba(255,255,0,0.1)",
                  }}
                >
                  ★ SIGN UP FREE
                </motion.button>
              )}
              <Link to="/championship" onClick={() => audio.click()}>
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  className="pk text-xs px-6 py-3 border tracking-widest"
                  style={{
                    color: "var(--accent-cyan)",
                    borderColor: "var(--accent-cyan)",
                    background: "rgba(0,255,255,0.1)",
                  }}
                >
                  ► VIEW LEADERBOARD
                </motion.button>
              </Link>
              <Link to="/arena" onClick={() => audio.click()}>
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  className="pk text-xs px-6 py-3 border tracking-widest"
                  style={{
                    color: "var(--accent-green)",
                    borderColor: "var(--accent-green)",
                    background: "rgba(0,255,65,0.1)",
                  }}
                >
                  ► WATCH ARENA LIVE
                </motion.button>
              </Link>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer
          className="pt-4 pk text-[7px] tracking-widest text-center"
          style={{
            color: "var(--accent-green)",
            textShadow: "0 0 6px #00ff41, 0 0 12px rgba(0,255,65,0.5)",
          }}
        >
          POWERED BY SIX EMPIRES · ALL RIGHTS RESERVED · COPYRIGHT 2026
        </footer>
      </motion.div>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)}/>
    </div>
  )
}
