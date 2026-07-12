import { useEffect, useMemo, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Link } from "react-router-dom"
import { AGENTS } from "../components/AgentSprites.jsx"
import { audio } from "../ui/audio_engine.js"
import LiveBotsPanel from "../components/LiveBotsPanel.jsx"

const TARGET = 1_000_000
const START  = 1_000

// ── Real racers hook — polls /api/engine-state every 5s ─────────────────
function useRealRacers() {
  const [racers, setRacers] = useState([])
  const [live, setLive] = useState(false)
  useEffect(() => {
    let dead = false
    const poll = async () => {
      try {
        const r = await fetch("/api/engine-state", { cache: "no-store" })
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const data = await r.json()
        if (dead) return
        const agents = Array.isArray(data.agents) ? data.agents : []
        const mapped = agents.map(a => {
          const sprite = AGENTS.find(ag => ag.name?.toLowerCase() === a.name?.toLowerCase())
            || AGENTS[Math.abs(a.name?.charCodeAt(6) || 0) % AGENTS.length]
          return {
            id:       a.name?.toLowerCase().replace(/\s+/g, "_") || "?",
            agent:    sprite,
            balance:  a.capital || 1000,
            trades:   a.total_trades || 0,
            streak:   a.am_streak || 0,
            strategy: a.strategy_key || "?",
            risk:     a.risk_mode || "?",
          }
        }).sort((a, b) => b.balance - a.balance)
        setRacers(mapped)
        setLive(true)
      } catch { setLive(false) }
      if (!dead) setTimeout(poll, 5000)
    }
    poll()
    return () => { dead = true }
  }, [])
  return { racers, live }
}

export default function RacingArena() {
  const { racers, live } = useRealRacers()
  const [winner, setWinner] = useState(null)
  const [eventLog, setEventLog] = useState([])
  const logRef = useRef(null)

  // Check for winner from real data
  useEffect(() => {
    if (!racers.length) return
    const w = racers.find(r => r.balance >= TARGET)
    if (w && !winner) {
      setWinner(w)
      if (audio.partyMusic) audio.partyMusic()
      setTimeout(() => { if (audio.triumph) audio.triumph() }, 200)
    }
  }, [racers])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [eventLog.length])

  const restart = () => {
    setWinner(null)
    setEventLog([])
    audio.click?.()
  }

  return (
    <div className="relative min-h-screen qwr-crt">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 max-w-[1600px] mx-auto px-4 md:px-8 pt-20 pb-12 space-y-5"
      >
        {/* Title + restart */}
        <header className="qwr-panel p-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className="pk text-sm tracking-widest"
              style={{ color: "#00ff41", textShadow: "0 0 10px rgba(0,255,65,0.6)" }}
            >
              ► LIVE RACE ARENA
            </div>
            <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)]">
              8 AGENTS · RACE TO $1,000,000
            </div>
          </div>
          <div className="flex items-center gap-3">
            {winner ? (
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={restart}
                className="pk text-[10px] tracking-widest px-4 py-2 border"
                style={{
                  color: "#00ffff",
                  borderColor: "#00ffff",
                  background: "rgba(0,255,255,0.1)",
                }}
              >
                ↻ RESTART RACE
              </motion.button>
            ) : (
              <div className="pk text-[8px] tracking-widest flex items-center gap-2 text-[color:var(--green)]">
                <span
                  className="w-2 h-2"
                  style={{
                    background: "#00ff41",
                    boxShadow: "0 0 8px #00ff41",
                    animation: "qwr-blink 0.8s infinite",
                  }}
                />
                LIVE · RACE IN PROGRESS
              </div>
            )}
          </div>
        </header>

        {/* Real paper-bot ticker (above the simulated race) */}
        <LiveBotsPanel />

        {/* Winner banner */}
        <AnimatePresence>
          {winner && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="qwr-panel p-5 text-center"
              style={{
                boxShadow: `0 0 40px ${winner.agent.color}, 0 0 80px ${winner.agent.color}55`,
                background: `linear-gradient(180deg, ${winner.agent.color}22, rgba(8,15,30,0.9))`,
              }}
            >
              <div className="pk text-xs tracking-widest text-[color:var(--subdim)] mb-3">
                ★ CHAMPION CROWNED ★
              </div>
              <div
                className="pk text-2xl md:text-4xl"
                style={{
                  color: winner.agent.color,
                  textShadow: `0 0 24px ${winner.agent.color}, 0 0 48px ${winner.agent.color}99`,
                }}
              >
                {winner.agent.name} HIT $1,000,000!
              </div>
              <div className="mt-3 pk text-[10px] tracking-widest text-[color:var(--subdim)]">
                {winner.trades} trades · streak {winner.streak > 0 ? "+" : ""}{winner.streak}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Race track */}
        <section className="qwr-panel p-5 space-y-3">
          <div className="flex items-center justify-between pk text-[8px] tracking-widest text-[color:var(--subdim)]">
            <span>START · $1,000</span>
            <span>FINISH · $1,000,000 ★</span>
          </div>

          {/* Track lanes */}
          <div className="space-y-3">
            <AnimatePresence>
              {racers.map((r, idx) => {
                // Log-scale progress so $1K → $1M feels visual
                const pct = Math.min(
                  100,
                  Math.max(0, (Math.log10(Math.max(r.balance, 1)) - 3) / 3 * 100)
                )
                const isLead = idx === 0 && !winner
                const isChamp = winner?.id === r.id
                return (
                  <motion.div
                    key={r.id}
                    layout
                    transition={{ type: "spring", stiffness: 220, damping: 28 }}
                    className="flex items-center gap-3"
                  >
                    {/* Rank */}
                    <div
                      className="pk text-sm w-6 text-center"
                      style={{
                        color: idx === 0 ? "#ffff00" : idx === 1 ? "#c0ddf0" : idx === 2 ? "#cc8844" : "#4a7090",
                        textShadow: idx < 3 ? `0 0 6px currentColor` : "none",
                      }}
                    >
                      {idx + 1}
                    </div>

                    {/* Name */}
                    <div className="pk text-[10px] w-24" style={{ color: r.agent.color }}>
                      {r.agent.name}
                    </div>

                    {/* Track */}
                    <div
                      className="relative flex-1 h-10 border overflow-hidden"
                      style={{
                        borderColor: "var(--border)",
                        background:
                          "linear-gradient(90deg, rgba(8,15,30,0.8), rgba(11,21,37,0.5))",
                      }}
                    >
                      {/* Lane tick marks */}
                      {[10, 20, 30, 40, 50, 60, 70, 80, 90].map(x => (
                        <span
                          key={x}
                          className="absolute top-1/2 -translate-y-1/2 w-px h-3"
                          style={{ left: `${x}%`, background: "rgba(74,112,144,0.4)" }}
                        />
                      ))}

                      {/* Progress fill */}
                      <motion.div
                        className="absolute inset-y-0 left-0"
                        style={{
                          background: `linear-gradient(90deg, transparent, ${r.agent.color}55, ${r.agent.color}88)`,
                          boxShadow: `inset 0 0 12px ${r.agent.color}44`,
                        }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.6, ease: "easeOut" }}
                      />

                      {/* Racer sprite (moves with progress) */}
                      <motion.div
                        className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 flex items-center justify-center"
                        style={{
                          left: `${pct}%`,
                          width: 30, height: 30,
                          background: `linear-gradient(135deg, ${r.agent.color}44, transparent)`,
                          border: `1px solid ${r.agent.color}`,
                          boxShadow: isLead
                            ? `0 0 14px ${r.agent.color}, 0 0 28px ${r.agent.color}66`
                            : `0 0 6px ${r.agent.color}66`,
                          zIndex: 2,
                        }}
                        animate={
                          isChamp
                            ? { scale: [1, 1.4, 1], rotate: [0, 360, 720] }
                            : isLead
                            ? { y: [0, -2, 0] }
                            : {}
                        }
                        transition={
                          isChamp
                            ? { duration: 1.0, repeat: Infinity, ease: "easeInOut" }
                            : isLead
                            ? { duration: 0.7, repeat: Infinity, ease: "easeInOut" }
                            : {}
                        }
                      >
                        <r.agent.Sprite size={22} color={r.agent.color} />

                        {/* Trail */}
                        {isLead && (
                          <motion.div
                            className="absolute right-full top-1/2 -translate-y-1/2 h-0.5"
                            style={{
                              width: 40,
                              background: `linear-gradient(to left, ${r.agent.color}aa, transparent)`,
                            }}
                          />
                        )}
                      </motion.div>

                      {/* Finish line flag at 100% */}
                      <span
                        className="absolute top-0 bottom-0 right-0 w-1"
                        style={{
                          background: "repeating-linear-gradient(0deg, #ffffff 0 4px, #0b1525 4px 8px)",
                        }}
                      />
                    </div>

                    {/* Balance */}
                    <div
                      className="pk text-[11px] w-28 text-right"
                      style={{ color: r.agent.color, textShadow: `0 0 4px ${r.agent.color}80` }}
                    >
                      ${Math.round(r.balance).toLocaleString()}
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>
          </div>
        </section>

        {/* Stats + event feed */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Top 3 quick cards */}
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-4">
            {racers.slice(0, 3).map((r, i) => (
              <div
                key={r.id}
                className="qwr-panel p-4"
                style={{
                  boxShadow: i === 0 ? `0 0 20px ${r.agent.color}55` : "none",
                }}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div
                    className="w-10 h-10 flex items-center justify-center"
                    style={{
                      background: `linear-gradient(135deg, ${r.agent.color}22, transparent)`,
                      border: `1px solid ${r.agent.color}`,
                    }}
                  >
                    <r.agent.Sprite size={30} color={r.agent.color} />
                  </div>
                  <div>
                    <div className="pk text-[10px]" style={{ color: r.agent.color }}>
                      {r.agent.name}
                    </div>
                    <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)]">
                      {i === 0 ? "LEADER" : i === 1 ? "2ND" : "3RD"}
                    </div>
                  </div>
                </div>
                <div
                  className="pk text-lg"
                  style={{ color: r.agent.color, textShadow: `0 0 6px ${r.agent.color}66` }}
                >
                  ${Math.round(r.balance).toLocaleString()}
                </div>
                <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mt-1">
                  {r.trades} TRADES · STREAK {r.streak >= 0 ? "+" : ""}{r.streak}
                </div>
              </div>
            ))}
          </div>

          {/* Event feed */}
          <div className="qwr-panel p-4 flex flex-col">
            <div
              className="pk text-[10px] tracking-widest mb-2"
              style={{ color: "#00ff41", textShadow: "0 0 8px rgba(0,255,65,0.5)" }}
            >
              ● LIVE FEED
            </div>
            <div
              ref={logRef}
              className="flex-1 overflow-y-auto mono text-[10px] leading-relaxed pr-1 space-y-0.5"
              style={{
                maxHeight: 220,
                background: "rgba(11,21,37,0.35)",
                padding: 8,
                border: "1px solid var(--border)",
              }}
            >
              {eventLog.map(l => (
                <div key={l.id} className="flex gap-2 items-baseline">
                  <span className="text-[color:var(--subdim)]">{l.ts}</span>
                  <span style={{ color: l.agent.color, textShadow: `0 0 3px ${l.agent.color}44` }}>
                    {l.agent.name}
                  </span>
                  <span className="text-[color:var(--text)]">· {l.msg}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Nav CTAs */}
        <section className="flex items-center justify-center gap-3 flex-wrap">
          <Link to="/dashboard" onClick={() => audio.click?.()}>
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.96 }}
              className="pk text-[10px] px-5 py-2 border tracking-widest"
              style={{ color: "#00ffff", borderColor: "#00ffff", background: "rgba(0,255,255,0.08)" }}
            >
              ◄ MY DASHBOARD
            </motion.button>
          </Link>
          <Link to="/championship" onClick={() => audio.click?.()}>
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.96 }}
              className="pk text-[10px] px-5 py-2 border tracking-widest"
              style={{ color: "#ffff00", borderColor: "#ffff00", background: "rgba(255,255,0,0.08)" }}
            >
              CHAMPIONSHIP ►
            </motion.button>
          </Link>
        </section>

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
