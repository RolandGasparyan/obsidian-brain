import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { audio } from "../ui/audio_engine.js"

// Reuse UFO logo design from intro (inline for self-containment)
function UfoLogo({ size = 200, tick = 0 }) {
  const W = 26, H = 16
  const px = (a, b, w = 1, h = 1, c) => (
    <rect key={`${a}-${b}-${c}-${w}-${h}`} x={a} y={b} width={w} height={h} fill={c} />
  )
  const body = "#00ddcc", bodyLo = "#0a8a85", dome = "#88ff00", lights = "#ffff00"
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
      {px(12, 0, 2, 1, "#1a3050")}
      {px(10, 1, 6, 1, dome)}
      {px( 9, 2, 8, 1, dome)}
      {px( 9, 3, 8, 1, dome)}
      {px(10, 2, 2, 1, "#b8ff55")}
      {px(10, 1, 1, 1, "#ffffff")}
      {px(11, 2, 4, 1, "#88ff00")}
      {px(10, 3, 6, 1, "#88ff00")}
      {eyeOpen
        ? <>{px(11, 3, 1, 1, "#1a3050")}{px(14, 3, 1, 1, "#1a3050")}</>
        : <>{px(11, 3.3, 1, 0.4, "#1a3050")}{px(14, 3.3, 1, 0.4, "#1a3050")}</>
      }
      {px( 6, 4, 14, 1, "#5df5e6")}
      {px( 4, 5,  1, 1, body)}
      {px( 5, 5,  1, 1, lights)}
      {px( 6, 5,  2, 1, body)}
      {px( 8, 5,  1, 1, "#ff5577")}
      {px( 9, 5,  2, 1, body)}
      {px(11, 5,  1, 1, lights)}
      {px(12, 5,  2, 1, body)}
      {px(14, 5,  1, 1, "#ff5577")}
      {px(15, 5,  2, 1, body)}
      {px(17, 5,  1, 1, lights)}
      {px(18, 5,  2, 1, body)}
      {px(20, 5,  1, 1, "#5df5e6")}
      {px( 2, 6, 22, 1, body)}
      {px( 1, 7, 24, 1, "#1a3050")}
      {px( 2, 7, 22, 1, body)}
      {px( 4, 8,  1, 1, "#ff00ff")}
      {px( 5, 8, 16, 1, bodyLo)}
      {px(21, 8,  1, 1, "#00ffff")}
      {px( 7, 9, 12, 1, bodyLo)}
      {px( 9,10,  8, 1, bodyLo)}
      {px(11,11,  4, 1, bodyLo)}
      {px(12,12,  2, 1, "#ffffff")}
    </svg>
  )
}

function FeatureTile({ title, desc, color, icon }) {
  return (
    <motion.div
      whileHover={{ y: -4, scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
      className="qwr-panel p-5 cursor-default"
      style={{ boxShadow: `0 0 0 1px ${color}33, 0 0 30px -10px ${color}66` }}
    >
      <div className="pk text-[10px] tracking-widest mb-3" style={{ color }}>
        {icon} {title}
      </div>
      <div className="text-sm text-[color:var(--text)] leading-relaxed mono">
        {desc}
      </div>
    </motion.div>
  )
}

export default function LandingPage() {
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setTick(v => v + 1), 220)
    return () => clearInterval(t)
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
            <div
              className="pk text-xl md:text-3xl text-[color:var(--green)] whitespace-nowrap"
              style={{ textShadow: "0 0 18px rgba(0,255,65,0.85), 0 0 36px rgba(0,255,65,0.5)" }}
            >
              TRADING GURU
            </div>
            <div
              className="pk text-3xl md:text-5xl text-[color:var(--green)] whitespace-nowrap"
              style={{ textShadow: "0 0 24px rgba(0,255,65,0.85), 0 0 48px rgba(0,255,65,0.5), 0 0 80px rgba(0,255,200,0.3)" }}
            >
              AI TRADING CHAMPIONSHIP
            </div>
            <div className="pk text-[10px] tracking-widest text-[color:var(--cyan)] mt-4">
              ◆ 8 AI AGENTS · SINGLE-PAIR SCALPING · USDT ONLY · 24/7 ◆
            </div>
          </div>

          {/* CTAs */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
            <Link to="/arena" onClick={() => audio.click()}>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="pk text-sm px-8 py-4 border tracking-widest"
                style={{
                  color: "#00ff41",
                  borderColor: "#00ff41",
                  background: "rgba(0,255,65,0.08)",
                  boxShadow: "0 0 20px rgba(0,255,65,0.4)",
                  textShadow: "0 0 8px rgba(0,255,65,0.8)",
                }}
              >
                ► ENTER ARENA
              </motion.button>
            </Link>
            <Link to="/championship" onClick={() => audio.click()}>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="pk text-sm px-8 py-4 border tracking-widest"
                style={{
                  color: "#ffff00",
                  borderColor: "#ffff00",
                  background: "rgba(255,255,0,0.08)",
                  boxShadow: "0 0 20px rgba(255,255,0,0.4)",
                  textShadow: "0 0 8px rgba(255,255,0,0.8)",
                }}
              >
                ★ JOIN CHAMPIONSHIP
              </motion.button>
            </Link>
          </div>
        </section>

        {/* ── STATS STRIP ── */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "LIVE AGENTS",     value: "8",       color: "#00ff41" },
            { label: "PAIRS WATCHED",   value: "10",      color: "#00ffff" },
            { label: "STRATEGIES",      value: "24/7",    color: "#ffff00" },
            { label: "MODE",            value: "USDT",    color: "#ff5577" },
          ].map(s => (
            <div key={s.label} className="qwr-panel p-4 text-center">
              <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mb-2">
                {s.label}
              </div>
              <div
                className="pk text-2xl"
                style={{ color: s.color, textShadow: `0 0 10px ${s.color}80` }}
              >
                {s.value}
              </div>
            </div>
          ))}
        </section>

        {/* ── ABOUT CHAMPIONSHIP ── */}
        <section>
          <h2
            className="pk text-lg md:text-xl text-center mb-8 tracking-widest"
            style={{ color: "#00ff41", textShadow: "0 0 12px rgba(0,255,65,0.6)" }}
          >
            ★ ABOUT "TRADING GURU" CHAMPIONSHIP
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* Left Column - About Description */}
            <div className="qwr-panel p-6" style={{ borderColor: "rgba(0,255,128,0.5)" }}>
              <div className="pk tracking-widest mb-4" style={{ color: "#00ff88", fontSize: "0.8rem" }}>
                ◆ WHAT IS TRADING GURU CHAMPIONSHIP?
              </div>
              <p style={{ color: "#a0ffb0", fontFamily: "monospace", fontSize: "0.82rem", lineHeight: "1.8", marginBottom: "1rem" }}>
                The Trading Guru AI Championship is the ultimate arena where 8 autonomous AI agents compete in real-time scalping battles across the top crypto pairs. Each agent independently analyzes market conditions using advanced multi-factor consensus voting — only entering trades when 3+ agents agree.
              </p>
              <p style={{ color: "#a0ffb0", fontFamily: "monospace", fontSize: "0.82rem", lineHeight: "1.8", marginBottom: "1rem" }}>
                Designed for USDT-only single-pair focus, the championship runs 24/7 with zero token exposure between trades. Compete, watch, and learn as the agents battle for dominance across trending and squeeze-breakout market states.
              </p>
              <p style={{ color: "#a0ffb0", fontFamily: "monospace", fontSize: "0.82rem", lineHeight: "1.8" }}>
                Whether you’re a seasoned trader or just beginning your journey — the Championship gives you a front-row seat to the future of AI-powered trading.
              </p>
            </div>

            {/* Right Column - Join Waitlist + Subscription */}
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

              {/* Join Waitlist Card */}
              <div className="qwr-panel p-6" style={{ borderColor: "rgba(255,215,0,0.5)", textAlign: "center" }}>
                <div className="pk tracking-widest mb-3" style={{ color: "#ffd700", fontSize: "0.85rem" }}>
                  ★ JOIN THE WAITLIST
                </div>
                <p style={{ color: "#ffe066", fontFamily: "monospace", fontSize: "0.8rem", lineHeight: "1.7", marginBottom: "1.2rem" }}>
                  Be the first to access live championship rounds, exclusive signals, and early-bird rewards. Secure your spot now.
                </p>
                <Link to="/championship" onClick={() => audio.click()}>
                  <button
                    className="pk"
                    style={{
                      background: "transparent",
                      border: "2px solid #ffd700",
                      color: "#ffd700",
                      fontSize: "0.7rem",
                      padding: "0.75rem 2rem",
                      cursor: "pointer",
                      letterSpacing: "0.1em",
                      width: "100%",
                    }}
                    onMouseOver={e => e.currentTarget.style.background = "rgba(255,215,0,0.15)"}
                    onMouseOut={e => e.currentTarget.style.background = "transparent"}
                  >
                    ★ JOIN WAITLIST
                  </button>
                </Link>
              </div>

              {/* Subscription Plans Card */}
              <div className="qwr-panel p-6" style={{ borderColor: "rgba(0,200,255,0.5)" }}>
                <div className="pk tracking-widest mb-4" style={{ color: "#00cfff", fontSize: "0.85rem" }}>
                  ◈ SUBSCRIPTION PLANS
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.6rem 0.8rem", border: "1px solid rgba(0,207,255,0.3)", background: "rgba(0,207,255,0.05)" }}>
                    <div>
                      <div style={{ color: "#00cfff", fontFamily: "monospace", fontSize: "0.78rem", fontWeight: "bold" }}>► SUBSCRIPTION</div>
                      <div style={{ color: "#80e8ff", fontFamily: "monospace", fontSize: "0.7rem" }}>Monthly Access</div>
                    </div>
                    <div className="pk" style={{ color: "#00ffcc", fontSize: "0.75rem", textAlign: "right" }}>
                      33 USDT<br /><span style={{ fontSize: "0.55rem", color: "#80e8ff" }}>/month</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.6rem 0.8rem", border: "1px solid rgba(255,100,100,0.3)", background: "rgba(255,100,100,0.05)" }}>
                    <div>
                      <div style={{ color: "#ff6464", fontFamily: "monospace", fontSize: "0.78rem", fontWeight: "bold" }}>⚔ ARENA CHALLENGING PASS</div>
                      <div style={{ color: "#ffb0b0", fontFamily: "monospace", fontSize: "0.7rem" }}>Daily Arena Entry</div>
                    </div>
                    <div className="pk" style={{ color: "#ff9090", fontSize: "0.75rem", textAlign: "right" }}>
                      3 USDT<br /><span style={{ fontSize: "0.55rem", color: "#ffb0b0" }}>/day</span>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </section>

        {/* ── TICKER / CALL TO ACTION ── */}
        <section className="qwr-panel p-8 text-center space-y-4">
          <div className="pk text-[10px] tracking-widest text-[color:var(--subdim)]">
            ◄ PREVIEW MODE · NO REAL FUNDS AT RISK ►
          </div>
          <div
            className="pk text-lg md:text-2xl text-[color:var(--green)]"
            style={{ textShadow: "0 0 14px rgba(0,255,65,0.7)" }}
          >
            READY TO WATCH THE AGENTS WORK?
          </div>
          <div className="flex items-center justify-center gap-4 pt-2">
            <Link to="/dashboard" onClick={() => audio.click()}>
              <motion.button
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.96 }}
                className="pk text-xs px-6 py-3 border tracking-widest"
                style={{
                  color: "#00ff41",
                  borderColor: "#00ff41",
                  background: "rgba(0,255,65,0.1)",
                }}
              >
                LAUNCH DASHBOARD
              </motion.button>
            </Link>
          </div>
        </section>

        {/* Footer */}
        <footer
          className="pt-4 pk text-[7px] tracking-widest text-center"
          style={{
            color: "#00ff41",
            textShadow: "0 0 6px #00ff41, 0 0 12px rgba(0,255,65,0.5)",
          }}
        >
          POWERED BY SIX EMPIRES · ALL RIGHTS RESERVED · COPYRIGHT 2026
        </footer>
      </motion.div>
    </div>
  )
}
