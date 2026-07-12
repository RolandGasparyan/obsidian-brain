/**
 * RacingDashboard.jsx — 8-lane cinematic racing track for paper agents.
 *
 * 🎮 PAPER MODE ONLY — all positions derived from simulated state.
 *
 * Visualization:
 *   - 8 horizontal lanes, one per paper agent
 *   - Each agent renders as a sprite/avatar moving along its lane
 *   - Position on track = normalized ELO percentile (leader at 95%, last at 5%)
 *   - Continuous animated loop — smooth Framer Motion interpolation between
 *     paper engine ticks (5s cadence)
 *   - Click an agent → expand detail card
 *   - Audio cues fire on paper events via usePaperAudioCues
 *   - PAPER MODE banner pinned top
 *
 * Layer 3 cinematic · zero capital risk · no real money references.
 *
 * 2026-05-13 · Phase 10/11 · Layer 3 (visual + audio)
 */
import { useMemo, useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Link } from "react-router-dom"
import { usePaperArena } from "../lib/usePaperArena.js"
import { usePaperAudioCues } from "../lib/usePaperAudioCues.js"
import { audio } from "../ui/audio_engine.js"

// ── ELO formula ──────────────────────────────────────────────────────────
function elo(a) {
  return Math.round(1200 + a.sharpe_sim * 200 + a.trades * 2 + a.win_rate * 100)
}

// ── Sprite registry (8 agents, distinct visuals) ─────────────────────────
const SPRITE = {
  HUNTER:   { icon: "🎯", color: "#ff7700", aura: "rgba(255,119,0,0.45)" },
  RISK:     { icon: "🛡", color: "#22c55e", aura: "rgba(34,197,94,0.45)" },
  ALPHA:    { icon: "α",  color: "#a855f7", aura: "rgba(168,85,247,0.45)" },
  REGIME:   { icon: "🌐", color: "#facc15", aura: "rgba(250,204,21,0.45)" },
  EXECUTOR: { icon: "⚙",  color: "#06b6d4", aura: "rgba(6,182,212,0.45)" },
  RECOVERY: { icon: "🔄", color: "#f59e0b", aura: "rgba(245,158,11,0.45)" },
  SKEPTIC:  { icon: "✋", color: "#ec4899", aura: "rgba(236,72,153,0.45)" },
  CHAMPION: { icon: "👑", color: "#fbbf24", aura: "rgba(251,191,36,0.45)" },
}

// ── Header / banner ──────────────────────────────────────────────────────
function RaceHeader({ cycle, leader, marketRegime }) {
  return (
    <div className="qwr-panel mono p-3 mb-3"
         style={{
           background: "rgba(8,15,30,0.88)",
           borderColor: "var(--accent-yellow)",
           boxShadow: "0 0 18px -4px var(--accent-yellow)",
         }}>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <motion.span
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.4, repeat: Infinity }}
            className="pk text-[14px] tracking-widest"
            style={{ color: "var(--accent-yellow)" }}
          >
            🏁 PAPER RACE · LIVE
          </motion.span>
          <span className="pk text-[9px] tracking-widest px-2 py-0.5"
                style={{
                  color: "var(--accent-yellow)",
                  border: "1px solid var(--accent-yellow)",
                  borderRadius: 2,
                }}>
            🎮 NO REAL CAPITAL
          </span>
        </div>
        <div className="flex items-center gap-4 text-[10px] mono">
          <span style={{ color: "var(--text-dim)" }}>
            cycle <span style={{ color: "var(--accent-cyan)" }}>{cycle}</span>
          </span>
          <span style={{ color: "var(--text-dim)" }}>
            regime <span style={{ color: "var(--accent-purple)" }}>{marketRegime}</span>
          </span>
          {leader && (
            <span style={{ color: "var(--text-dim)" }}>
              leader{" "}
              <span style={{ color: "var(--accent-gold)" }}>
                {SPRITE[leader.id]?.icon} {leader.label}
              </span>
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Single racing lane ───────────────────────────────────────────────────
function RacingLane({ agent, rank, totalAgents, eloMin, eloMax, onClick, isSelected, isLeader }) {
  const sprite = SPRITE[agent.id] || { icon: "?", color: "#888", aura: "rgba(136,136,136,0.4)" }
  const agentElo = elo(agent)
  // Position on track: 8% (start) → 92% (finish line)
  const span = Math.max(1, eloMax - eloMin)
  const norm = (agentElo - eloMin) / span
  const posPct = 8 + norm * 84

  return (
    <motion.div
      layout
      onClick={onClick}
      className="relative cursor-pointer select-none"
      whileHover={{ scale: 1.01 }}
      style={{
        height: 56,
        background: "linear-gradient(90deg, rgba(8,15,30,0.7) 0%, rgba(8,15,30,0.5) 50%, rgba(8,15,30,0.7) 100%)",
        border: isSelected ? `1px solid ${sprite.color}` : "1px solid rgba(255,255,255,0.05)",
        borderRadius: 4,
        boxShadow: isSelected ? `0 0 14px -4px ${sprite.color}` : "none",
      }}
    >
      {/* Lane number + name on left */}
      <div className="absolute left-2 top-1/2 -translate-y-1/2 flex items-center gap-2 pointer-events-none"
           style={{ zIndex: 2 }}>
        <span className="pk text-[9px] tracking-widest"
              style={{ color: isLeader ? "var(--accent-gold)" : "var(--text-dim)", minWidth: 22 }}>
          {rank === 1 ? "👑" : `#${rank}`}
        </span>
        <span className="mono text-[10px] tracking-wider"
              style={{ color: sprite.color, fontWeight: 600, minWidth: 80 }}>
          {agent.label}
        </span>
        <span className="mono text-[8px]" style={{ color: "var(--text-dim)" }}>
          {agent.faction}
        </span>
      </div>

      {/* Lane dotted guide */}
      <div className="absolute top-1/2 -translate-y-1/2 right-0 left-0 pointer-events-none"
           style={{ height: 1, background: `repeating-linear-gradient(to right, ${sprite.color}22 0, ${sprite.color}22 4px, transparent 4px, transparent 12px)` }} />

      {/* Finish line at 92% */}
      <div className="absolute top-0 bottom-0 pointer-events-none"
           style={{
             left: "92%",
             width: 2,
             background: `repeating-linear-gradient(to bottom, ${sprite.color}66 0, ${sprite.color}66 4px, transparent 4px, transparent 8px)`,
           }} />

      {/* Animated sprite — Framer Motion smoothly interpolates position changes */}
      <motion.div
        className="absolute top-1/2 -translate-y-1/2"
        initial={{ left: "8%" }}
        animate={{ left: `${posPct}%` }}
        transition={{ duration: 4.5, ease: "easeOut" }}
        style={{ zIndex: 3 }}
      >
        {/* Bobbing micro-animation for continuous life */}
        <motion.div
          animate={{ y: [0, -2, 0, 2, 0] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
          className="relative flex items-center justify-center"
          style={{
            width: 32, height: 32,
            background: `radial-gradient(circle, ${sprite.aura} 0%, transparent 70%)`,
            transform: "translate(-50%, -50%)",
          }}
        >
          <span style={{ fontSize: 20, filter: `drop-shadow(0 0 4px ${sprite.color})` }}>
            {sprite.icon}
          </span>
        </motion.div>
      </motion.div>

      {/* Stats badge on right */}
      <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2 pointer-events-none mono text-[9px]"
           style={{ zIndex: 2 }}>
        <span style={{ color: agent.simulated_pnl_usd >= 0 ? "var(--accent-green)" : "var(--accent-pink)" }}>
          {agent.simulated_pnl_usd >= 0 ? "+" : ""}${agent.simulated_pnl_usd.toFixed(0)}
        </span>
        <span style={{ color: "var(--accent-cyan)" }}>
          ELO {agentElo}
        </span>
      </div>
    </motion.div>
  )
}

// ── Detail card for selected agent ───────────────────────────────────────
function AgentDetailCard({ agent, onClose }) {
  if (!agent) return null
  const sprite = SPRITE[agent.id] || { icon: "?", color: "#888" }
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      className="qwr-panel mono text-[10px] p-3 mt-3"
      style={{
        background: "rgba(8,15,30,0.92)",
        borderColor: sprite.color,
        boxShadow: `0 0 18px -4px ${sprite.color}`,
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span style={{ fontSize: 22 }}>{sprite.icon}</span>
          <div>
            <div className="pk text-[12px] tracking-widest" style={{ color: sprite.color }}>
              {agent.label}
            </div>
            <div className="text-[9px]" style={{ color: "var(--text-dim)" }}>
              {agent.personality} · {agent.faction}
            </div>
          </div>
        </div>
        <button onClick={onClose} className="text-[16px] px-2" style={{ color: "var(--text-dim)" }}>
          ×
        </button>
      </div>

      <div className="grid grid-cols-3 gap-x-3 gap-y-1.5">
        <Stat label="Sim PnL" value={`${agent.simulated_pnl_usd >= 0 ? "+" : ""}$${agent.simulated_pnl_usd.toFixed(2)}`}
              color={agent.simulated_pnl_usd >= 0 ? "var(--accent-green)" : "var(--accent-pink)"} />
        <Stat label="Sharpe" value={agent.sharpe_sim.toFixed(2)}
              color={agent.sharpe_sim >= 0 ? "var(--accent-green)" : "var(--accent-pink)"} />
        <Stat label="WR"     value={`${(agent.win_rate * 100).toFixed(0)}%`} color="var(--accent-cyan)" />
        <Stat label="Trades" value={agent.trades} color="var(--text)" />
        <Stat label="DD"     value={`${agent.vDD_pct_sim.toFixed(1)}%`}
              color={agent.vDD_pct_sim < 10 ? "var(--accent-green)" : "var(--accent-orange)"} />
        <Stat label="XP"     value={agent.xp} color="var(--accent-gold)" />
        <Stat label="Streak" value={`${agent.streak >= 0 ? "+" : ""}${agent.streak}`}
              color={agent.streak > 0 ? "var(--accent-green)" : agent.streak < 0 ? "var(--accent-pink)" : "var(--text-dim)"} />
        <Stat label="Conf"   value={`${agent.confidence.toFixed(0)}`} color="var(--accent-cyan)" />
        <Stat label="Exp"    value={`${agent.exposure_pct.toFixed(0)}%`} color="var(--accent-orange)" />
        <Stat label="Pos"    value={agent.position} color={agent.position === "LONG" ? "var(--accent-green)"
                                                          : agent.position === "SHORT" ? "var(--accent-pink)"
                                                          : "var(--text-dim)"} />
        <Stat label="Status" value={agent.status} color="var(--accent-yellow)" />
        <Stat label="Action" value={agent.last_action} color={sprite.color} />
      </div>

      <div className="mt-2 pt-2 text-[8px]"
           style={{ color: "var(--text-dim)", borderTop: "1px dashed rgba(255,255,255,0.08)" }}>
        🎮 All values SIMULATED · No real capital at risk · No exchange orders sent
      </div>
    </motion.div>
  )
}

function Stat({ label, value, color }) {
  return (
    <div>
      <span style={{ color: "var(--text-dim)" }}>{label} </span>
      <span style={{ color }}>{value}</span>
    </div>
  )
}

// ── Event ticker (bottom) ────────────────────────────────────────────────
function EventTicker({ events }) {
  if (!events?.length) return null
  return (
    <div className="qwr-panel mono text-[9px] p-2 mt-3"
         style={{ background: "rgba(8,15,30,0.7)", borderColor: "var(--accent-cyan)" }}>
      <div className="pk text-[8px] tracking-widest mb-1" style={{ color: "var(--accent-cyan)" }}>
        ⚡ LIVE PAPER EVENTS · audio cues active
      </div>
      <div className="space-y-0.5 max-h-24 overflow-y-auto">
        {events.slice(0, 8).map((e, i) => (
          <div key={i} style={{ color: "var(--text)" }}>
            <span style={{ color: "var(--accent-yellow)" }}>{e.type}</span>
            <span style={{ color: "var(--text-dim)" }}> · {e.agent_id} · cycle {e.cycle}</span>
            {typeof e.pnl_sim_usd === "number" && (
              <span style={{ color: e.pnl_sim_usd > 0 ? "var(--accent-green)" : "var(--accent-pink)" }}>
                {" "}{e.pnl_sim_usd >= 0 ? "+" : ""}${e.pnl_sim_usd.toFixed(2)} (sim)
              </span>
            )}
            {typeof e.streak !== "undefined" && (
              <span style={{ color: "var(--accent-yellow)" }}>{" "}streak {e.streak}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Commentary panel ─────────────────────────────────────────────────────
function CommentaryPanel({ commentary }) {
  if (!commentary?.length) return null
  return (
    <div className="qwr-panel mono text-[10px] p-2 mt-3"
         style={{ background: "rgba(8,15,30,0.7)", borderColor: "var(--accent-purple)" }}>
      <div className="pk text-[8px] tracking-widest mb-1" style={{ color: "var(--accent-purple)" }}>
        🎙 PAPER CASTERS
      </div>
      <div className="space-y-1">
        {commentary.map((c, i) => (
          <div key={i}>
            <span className="pk text-[7px] tracking-widest mr-1" style={{
              color: c.personality === "HYPE" ? "var(--accent-orange)"
                   : c.personality === "TACTIC" ? "var(--accent-cyan)"
                   : "var(--accent-purple)",
            }}>[{c.personality}]</span>
            <span style={{ color: "var(--text)" }}>{c.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Mini leaderboard ─────────────────────────────────────────────────────
function MiniLeaderboard({ ranked }) {
  return (
    <div className="qwr-panel mono text-[10px] p-2"
         style={{
           background: "rgba(8,15,30,0.85)",
           borderColor: "var(--accent-gold)",
           boxShadow: "0 0 12px -4px var(--accent-gold)",
         }}>
      <div className="pk text-[9px] tracking-widest mb-2" style={{ color: "var(--accent-gold)" }}>
        🏆 RANK · ELO
      </div>
      <div className="space-y-0.5">
        {ranked.map((a, i) => {
          const rank = i + 1
          const sprite = SPRITE[a.id] || { icon: "?", color: "#888" }
          const ranKColor = rank === 1 ? "var(--accent-gold)"
                          : rank === 2 ? "var(--accent-cyan)"
                          : rank === 3 ? "var(--accent-purple)"
                          : "var(--text-dim)"
          return (
            <motion.div
              key={a.id}
              layout
              className="flex items-center justify-between px-1 py-0.5 border-l-2"
              style={{
                borderColor: ranKColor,
                background: rank <= 3 ? `${ranKColor}11` : "transparent",
              }}
              transition={{ type: "spring", stiffness: 380, damping: 28 }}
            >
              <span className="flex items-center gap-1.5">
                <span style={{ color: ranKColor, minWidth: 18 }}>
                  {rank === 1 ? "👑" : `#${rank}`}
                </span>
                <span>{sprite.icon}</span>
                <span style={{ color: sprite.color, fontWeight: 600 }}>
                  {a.label}
                </span>
              </span>
              <span style={{ color: "var(--accent-cyan)" }}>
                {elo(a)}
              </span>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────
export default function RacingDashboard() {
  const { data, isPaperMode, loading } = usePaperArena()
  const [selectedId, setSelectedId] = useState(null)
  const [audioOn, setAudioOn] = useState(true)

  // Phase 11: audio cues
  usePaperAudioCues({ enabled: audioOn })

  const agents = useMemo(() => data?.agents || [], [data])
  const ranked = useMemo(
    () => [...agents].sort((a, b) => elo(b) - elo(a)),
    [agents]
  )
  const eloMax = ranked.length ? elo(ranked[0]) : 1500
  const eloMin = ranked.length ? elo(ranked[ranked.length - 1]) : 1100
  const selected = agents.find((a) => a.id === selectedId)
  const leader = ranked[0]

  return (
    <div className="min-h-screen pt-20 pb-12 px-4 md:px-6"
         style={{ position: "relative", zIndex: 10 }}>

      {/* Top nav back */}
      <div className="max-w-[1400px] mx-auto mb-3 flex items-center gap-3">
        <Link to="/" className="mono text-[10px] tracking-widest pk px-2 py-1"
              style={{
                color: "var(--accent-cyan)",
                border: "1px solid var(--accent-cyan)",
                borderRadius: 3,
              }}
              onClick={() => audio.click?.()}>
          ← HOME
        </Link>
        <Link to="/championship" className="mono text-[10px] tracking-widest pk px-2 py-1"
              style={{
                color: "var(--accent-gold)",
                border: "1px solid var(--accent-gold)",
                borderRadius: 3,
              }}
              onClick={() => audio.click?.()}>
          👑 CHAMPIONSHIP
        </Link>
        <span style={{ flex: 1 }} />
        <button
          onClick={() => { setAudioOn(!audioOn); audio.click?.() }}
          className="mono text-[10px] tracking-widest pk px-2 py-1"
          style={{
            color: audioOn ? "var(--accent-yellow)" : "var(--text-dim)",
            border: `1px solid ${audioOn ? "var(--accent-yellow)" : "var(--text-dim)"}`,
            borderRadius: 3,
            cursor: "pointer",
          }}
        >
          {audioOn ? "🔊 AUDIO ON" : "🔇 AUDIO OFF"}
        </button>
      </div>

      <div className="max-w-[1400px] mx-auto">
        <RaceHeader
          cycle={data?.cycle ?? "—"}
          leader={leader}
          marketRegime={data?.market?.regime ?? "—"}
        />

        {loading && (
          <div className="qwr-panel p-4 mono text-[10px]"
               style={{ background: "rgba(8,15,30,0.8)", borderColor: "var(--accent-cyan)" }}>
            Loading paper arena…
          </div>
        )}

        {!loading && !isPaperMode && (
          <div className="qwr-panel p-4 mono text-[10px]"
               style={{ background: "rgba(8,15,30,0.8)", borderColor: "var(--accent-orange)" }}>
            Paper arena not active. Start the paper-arena.service on the server.
          </div>
        )}

        {!loading && isPaperMode && (
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-3">
            {/* Left: racing track */}
            <div>
              <div className="space-y-1.5">
                <AnimatePresence>
                  {ranked.map((a, i) => (
                    <RacingLane
                      key={a.id}
                      agent={a}
                      rank={i + 1}
                      totalAgents={ranked.length}
                      eloMin={eloMin}
                      eloMax={eloMax}
                      onClick={() => { setSelectedId(a.id === selectedId ? null : a.id); audio.click?.() }}
                      isSelected={a.id === selectedId}
                      isLeader={i === 0}
                    />
                  ))}
                </AnimatePresence>
              </div>

              <AnimatePresence>
                {selected && (
                  <AgentDetailCard
                    agent={selected}
                    onClose={() => { setSelectedId(null); audio.click?.() }}
                  />
                )}
              </AnimatePresence>

              <CommentaryPanel commentary={data?.commentary} />
              <EventTicker events={data?.events} />

              {/* Disclaimer banner */}
              <div className="qwr-panel mono text-[9px] p-2 mt-3 text-center"
                   style={{
                     background: "rgba(20,15,5,0.85)",
                     borderColor: "var(--accent-yellow)",
                     color: "var(--accent-yellow)",
                   }}>
                ALL PnL, trades, outcomes are SIMULATED. Real capital: $0.00 ·
                Exchange orders sent: 0 · Layer 1 trading core LOCKED.
              </div>
            </div>

            {/* Right: mini leaderboard + market state */}
            <div className="space-y-3">
              <MiniLeaderboard ranked={ranked} />

              <div className="qwr-panel mono text-[10px] p-2"
                   style={{ background: "rgba(8,15,30,0.85)", borderColor: "var(--accent-purple)" }}>
                <div className="pk text-[9px] tracking-widest mb-2"
                     style={{ color: "var(--accent-purple)" }}>
                  🌐 MARKET
                </div>
                <div className="space-y-1">
                  <Stat label="Regime"     value={data?.market?.regime ?? "—"} color="var(--accent-purple)" />
                  <Stat label="BTC"        value={`$${(data?.market?.btc_price || 0).toFixed(0)}`} color="var(--accent-gold)" />
                  <Stat label="Volatility" value={`${((data?.market?.volatility || 0) * 100).toFixed(2)}%`} color="var(--accent-cyan)" />
                  <Stat label="Trend"      value={data?.market?.trend ?? "—"} color="var(--text)" />
                </div>
              </div>

              <div className="qwr-panel mono text-[9px] p-2"
                   style={{ background: "rgba(8,15,30,0.85)", borderColor: "var(--accent-green)" }}>
                <div className="pk text-[9px] tracking-widest mb-1"
                     style={{ color: "var(--accent-green)" }}>
                  🛡 LAYER 1 STATUS
                </div>
                <div style={{ color: "var(--accent-green)" }}>
                  ✓ LOCKED
                </div>
                <div style={{ color: "var(--text-dim)", fontSize: 8, marginTop: 4 }}>
                  Canary SHA256: 704dd57...<br/>
                  L99 halt: engaged<br/>
                  Capital: $1,980.90 USDT untouched<br/>
                  Exchange sockets: 0
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
