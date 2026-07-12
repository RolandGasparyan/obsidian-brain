import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Link } from "react-router-dom"
import { AGENTS } from "../components/AgentSprites.jsx"
import { audio } from "../ui/audio_engine.js"
import BetModal from "../components/BetModal.jsx"
import LiveBotsPanel from "../components/LiveBotsPanel.jsx"
import L99StatusPanel from "../components/L99StatusPanel.jsx"

// ── Countdown to next round ──
function useCountdown(targetDate) {
  const [remaining, setRemaining] = useState(Math.max(0, targetDate - Date.now()))
  useEffect(() => {
    const t = setInterval(() => setRemaining(Math.max(0, targetDate - Date.now())), 500)
    return () => clearInterval(t)
  }, [targetDate])
  const h = Math.floor(remaining / 3600000).toString().padStart(2, "0")
  const m = Math.floor((remaining % 3600000) / 60000).toString().padStart(2, "0")
  const s = Math.floor((remaining % 60000) / 1000).toString().padStart(2, "0")
  return { h, m, s, total: remaining }
}

// ── Real leaderboard hook — polls /api/engine-state every 5s ──────────────
function useRealLeaderboard() {
  const [board, setBoard] = useState([])
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
        const mapped = agents.map(a => ({
          id:      a.name?.toLowerCase().replace(/\s+/g, "_") || "?",
          name:    a.name || "?",
          roi:     +((((a.capital || 1000) - 1000) / 1000) * 100).toFixed(2),
          trades:  a.total_trades || 0,
          wins:    a.wins || 0,
          sharpe:  a.win_rate ? +(a.win_rate * 3).toFixed(2) : 0,
          streak:  a.am_streak || 0,
          capital: a.capital || 0,
          strategy:a.strategy_key || a.strategy || "?",
          risk:    a.risk_mode || "?",
        })).sort((a, b) => b.capital - a.capital)
        setBoard(mapped)
        setLive(true)
      } catch { setLive(false) }
      if (!dead) setTimeout(poll, 5000)
    }
    poll()
    return () => { dead = true }
  }, [])
  return { board, live }
}

export default function ChampionshipPage() {
  // Next round: 2h 17m from now
  const nextRound = Date.now() + 2 * 3600 * 1000 + 17 * 60 * 1000
  const { h, m, s } = useCountdown(nextRound)
  const { board, live } = useRealLeaderboard()
  const [flashId, setFlashId] = useState(null)
  const [betOpen, setBetOpen] = useState(false)

  const prizePool = 1000000       // 1M USDT target
  const topPayout = prizePool     // Winner takes all

  return (
    <div className="relative min-h-screen qwr-crt">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 0.61, 0.36, 1] }}
        className="relative z-10 max-w-[1400px] mx-auto px-4 md:px-8 pt-8 pb-16 space-y-8"
      >
        {/* ── Header nav ── */}
        <header className="flex items-center justify-between qwr-panel px-5 py-3 flex-wrap gap-3">
          <Link to="/" onClick={() => audio.click()}>
            <motion.div
              whileHover={{ x: -4 }}
              className="pk text-[10px] tracking-widest text-[color:var(--green)]"
              style={{ textShadow: "0 0 8px rgba(0,255,65,0.5)" }}
            >
              ◄ HOME
            </motion.div>
          </Link>
          <div
            className="pk text-sm md:text-lg text-[color:var(--green)] tracking-widest"
            style={{ textShadow: "0 0 10px rgba(0,255,65,0.6)" }}
          >
            ★ AI TRADING CHAMPIONSHIP ★
          </div>
          <Link to="/arena" onClick={() => audio.click()}>
            <motion.div
              whileHover={{ x: 4 }}
              className="pk text-[10px] tracking-widest text-[color:var(--cyan)]"
              style={{ textShadow: "0 0 8px rgba(0,255,255,0.5)" }}
            >
              DASHBOARD ►
            </motion.div>
          </Link>
        </header>

        {/* ── Top row: Countdown + Prize Pool + Status ── */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Countdown */}
          <div className="qwr-panel p-5 text-center">
            <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mb-3">
              ● NEXT ROUND STARTS IN
            </div>
            <div className="flex items-center justify-center gap-2">
              {[
                { label: "HRS", v: h },
                { label: "MIN", v: m },
                { label: "SEC", v: s },
              ].map((x, i) => (
                <div key={x.label} className="flex items-center gap-2">
                  <div>
                    <div
                      className="pk text-3xl text-[color:var(--green)]"
                      style={{ textShadow: "0 0 10px rgba(0,255,65,0.6)" }}
                    >
                      {x.v}
                    </div>
                    <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)]">
                      {x.label}
                    </div>
                  </div>
                  {i < 2 && <div className="pk text-2xl text-[color:var(--subdim)]">:</div>}
                </div>
              ))}
            </div>
          </div>

          {/* Prize pool */}
          <div className="qwr-panel p-5 text-center">
            <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mb-3">
              ◆ TARGET · WINNER TAKES ALL
            </div>
            <div
              className="pk text-3xl text-[color:var(--yellow)]"
              style={{ textShadow: "0 0 14px rgba(255,255,0,0.7)" }}
            >
              $1,000,000 USDT
            </div>
            <div className="mt-2 pk text-[8px] tracking-widest text-[color:var(--subdim)]">
              FIRST AGENT TO HIT THE MILLION WINS THE POT
            </div>
          </div>

          {/* Live Status */}
          <div className="qwr-panel p-5 text-center">
            <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mb-3">
              ▲ SESSION STATUS
            </div>
            <div
              className="pk text-xl text-[color:var(--green)] inline-flex items-center gap-2"
              style={{ textShadow: "0 0 8px rgba(0,255,65,0.5)" }}
            >
              <span
                className="w-2.5 h-2.5 inline-block"
                style={{
                  background: "#00ff41",
                  boxShadow: "0 0 10px #00ff41",
                  animation: "qwr-blink 0.9s infinite",
                }}
              />
              LIVE · ROUND 7
            </div>
            <div className="mt-3 flex justify-center gap-4 pk text-[8px] tracking-widest">
              <span className="text-[color:var(--subdim)}">
                <span className="text-[color:var(--cyan)]">24</span>/32 AGENTS
              </span>
              <span className="text-[color:var(--subdim)]">
                <span className="text-[color:var(--yellow)]">1D</span> REMAINING
              </span>
            </div>
          </div>
        </section>

        {/* ── L99 Champion-mode system status ── */}
        <L99StatusPanel />

        {/* ── LIVE BOTS (legacy spot Vote bots) ── */}
        <LiveBotsPanel />

        {/* ── LEADERBOARD (mock simulation for demo) ── */}
        <section className="qwr-panel p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div
              className="pk text-[12px] tracking-widest text-[color:var(--green)]"
              style={{ textShadow: "0 0 8px rgba(0,255,65,0.5)" }}
            >
              ► LIVE LEADERBOARD
            </div>
            <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)]">
              UPDATES · 2.5s
            </div>
          </div>

          {/* Header row */}
          <div className="grid grid-cols-12 gap-2 pk text-[8px] tracking-widest text-[color:var(--subdim)] border-b border-[color:var(--border)] pb-2">
            <div className="col-span-1 text-center">#</div>
            <div className="col-span-3">AGENT</div>
            <div className="col-span-2 text-right">ROI</div>
            <div className="col-span-2 text-right">TRADES</div>
            <div className="col-span-1 text-right">W</div>
            <div className="col-span-2 text-right">SHARPE</div>
            <div className="col-span-1 text-right">STREAK</div>
          </div>

          {/* Rows */}
          <AnimatePresence>
            {board.map((row, idx) => {
              const agent = AGENTS.find(a => a.id === row.id)
              const rankColor = idx === 0 ? "#ffff00" : idx === 1 ? "#c0ddf0" : idx === 2 ? "#cc8844" : "#4a7090"
              const wr = Math.round((row.wins / row.trades) * 100)
              const isFlash = flashId === row.id
              return (
                <motion.div
                  key={row.id}
                  layout
                  transition={{ type: "spring", stiffness: 300, damping: 26 }}
                  className="grid grid-cols-12 gap-2 items-center py-2.5 border-b border-[color:var(--border)]/60"
                  style={{
                    background: isFlash ? `${agent.color}15` : "transparent",
                    transition: "background 0.4s",
                  }}
                >
                  <div
                    className="col-span-1 text-center pk text-lg"
                    style={{ color: rankColor, textShadow: `0 0 8px ${rankColor}80` }}
                  >
                    {idx + 1}
                  </div>
                  <div className="col-span-3 flex items-center gap-3">
                    <div
                      className="w-9 h-9 flex items-center justify-center"
                      style={{
                        background: `linear-gradient(135deg, ${agent.color}22, transparent)`,
                        border: `1px solid ${agent.color}55`,
                      }}
                    >
                      <agent.Sprite size={28} color={agent.color} />
                    </div>
                    <div>
                      <div className="pk text-[11px]" style={{ color: agent.color }}>
                        {agent.name}
                      </div>
                      <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)]">
                        {agent.role}
                      </div>
                    </div>
                  </div>
                  <div
                    className="col-span-2 text-right pk text-sm"
                    style={{
                      color: row.roi >= 0 ? "#00ff41" : "#ff3333",
                      textShadow: `0 0 6px ${row.roi >= 0 ? "rgba(0,255,65,0.5)" : "rgba(255,51,51,0.5)"}`,
                    }}
                  >
                    {row.roi >= 0 ? "+" : ""}{row.roi.toFixed(1)}%
                  </div>
                  <div className="col-span-2 text-right pk text-sm text-[color:var(--text)]">
                    {row.trades}
                  </div>
                  <div className="col-span-1 text-right pk text-sm text-[color:var(--subdim)]">
                    {wr}%
                  </div>
                  <div className="col-span-2 text-right pk text-sm text-[color:var(--cyan)]">
                    {row.sharpe.toFixed(2)}
                  </div>
                  <div className="col-span-1 text-right pk text-sm">
                    {row.streak > 0 ? (
                      <span style={{ color: "#00ff41" }}>+{row.streak}</span>
                    ) : (
                      <span className="text-[color:var(--subdim)]">—</span>
                    )}
                  </div>
                </motion.div>
              )
            })}
          </AnimatePresence>
        </section>

        {/* ── RULES & ROADMAP ── */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Rules — RACE TO $1M USDT */}
          <div className="qwr-panel p-5 space-y-3">
            <div
              className="pk text-sm tracking-widest text-[color:var(--green)]"
              style={{ textShadow: "0 0 8px rgba(0,255,65,0.5)" }}
            >
              ◆ THE RULE — FIRST TO $1,000,000
            </div>
            <ul className="text-sm text-[color:var(--text)] mono space-y-2 leading-relaxed">
              <li>► All 8 agents start with $1,000 USDT</li>
              <li>► First agent to reach $1,000,000 balance <b style={{color:"#ffff00"}}>WINS THE ENTIRE POT</b></li>
              <li>► No 2nd, no 3rd — winner takes all</li>
              <li>► Max position size: 8% of balance per trade</li>
              <li>► 3.5% daily loss → 24h cooldown</li>
              <li>► Min 3/8 consensus required to enter long</li>
              <li>► Pair switch: 3 losses OR -1.5% pair PnL</li>
              <li>► 24/7 live — race continues until a millionaire emerges</li>
            </ul>
          </div>

          {/* Progress toward $1M for top 3 agents */}
          <div className="qwr-panel p-5 space-y-3">
            <div
              className="pk text-sm tracking-widest text-[color:var(--yellow)]"
              style={{ textShadow: "0 0 8px rgba(255,255,0,0.5)" }}
            >
              ★ RACE TO $1M — TOP 3
            </div>
            <div className="space-y-3">
              {board.slice(0, 3).map((row, i) => {
                const agent = AGENTS.find(a => a.id === row.id)
                // mock current balance scaled from roi (illustrative)
                const balance = Math.round(1000 * (1 + row.roi * 18))   // puts it in the tens/hundreds-of-thousands range
                const pct = Math.min(100, balance / 10000)              // balance / 1M × 100
                return (
                  <div key={row.id} className="flex items-center gap-3">
                    <div
                      className="pk text-[11px] tracking-widest"
                      style={{ color: agent.color, width: 90 }}
                    >
                      {i === 0 ? "1ST · " : i === 1 ? "2ND · " : "3RD · "}{agent.name}
                    </div>
                    <div className="flex-1 h-3 border border-[color:var(--border)] bg-[color:var(--panel)]">
                      <motion.div
                        className="h-full"
                        style={{
                          background: agent.color,
                          boxShadow: `0 0 6px ${agent.color}`,
                        }}
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 1.2, ease: "easeOut" }}
                      />
                    </div>
                    <div
                      className="pk text-[11px]"
                      style={{ color: agent.color, width: 110, textAlign: "right" }}
                    >
                      ${balance.toLocaleString()}
                    </div>
                  </div>
                )
              })}
            </div>
            <div className="pt-2 pk text-[8px] tracking-widest text-[color:var(--subdim)] text-center">
              DISTANCE REMAINING UNTIL A WINNER EMERGES
            </div>
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="qwr-panel p-8 text-center space-y-4">
          <div
            className="pk text-lg md:text-2xl text-[color:var(--green)]"
            style={{ textShadow: "0 0 14px rgba(0,255,65,0.7)" }}
          >
            ENTER THE ARENA · PLACE YOUR BET
          </div>
          <div className="pk text-[10px] tracking-widest text-[color:var(--subdim)]">
            WATCH 8 AGENTS BATTLE · BACK YOUR CHAMPION · WIN BIG
          </div>
          <div className="flex items-center justify-center gap-3 pt-2 flex-wrap">
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.96 }}
              onClick={() => { audio.click?.(); setBetOpen(true) }}
              className="pk text-sm px-8 py-3 border tracking-widest"
              style={{
                color: "#ffff00",
                borderColor: "#ffff00",
                background: "rgba(255,255,0,0.1)",
                boxShadow: "0 0 20px rgba(255,255,0,0.5)",
                textShadow: "0 0 8px rgba(255,255,0,0.8)",
              }}
            >
              ★ PLACE BET
            </motion.button>
            <Link to="/arena" onClick={() => audio.click()}>
              <motion.button
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.96 }}
                className="pk text-sm px-8 py-3 border tracking-widest"
                style={{
                  color: "#00ff41",
                  borderColor: "#00ff41",
                  background: "rgba(0,255,65,0.1)",
                  boxShadow: "0 0 16px rgba(0,255,65,0.35)",
                }}
              >
                WATCH LIVE ►
              </motion.button>
            </Link>
          </div>
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

      <BetModal open={betOpen} onClose={() => setBetOpen(false)} />
    </div>
  )
}
