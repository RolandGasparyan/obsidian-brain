/**
 * ChampionshipOverlay.jsx — Real Layer 3 championship UI on top of phase_x20 stubs.
 *
 * Builds on parallel team's scaffolds:
 *   - economy/XPWallet.js     (XP calc)
 *   - casters/AICasterSystem.js (3 commentator personalities)
 *   - factions/FactionEngine.js (4 factions)
 *   - dna/MarketDNAEngine.js   (regime classification)
 *   - memory/AgentMemoryEngine.js (per-agent state)
 *   - director/CinematicDirector.js (camera modes)
 *
 * Plus real implementations driven by useTerminalDeltas:
 *   - Live XP/ELO leaderboard
 *   - 3-personality commentator stream
 *   - Rivalry detection
 *   - Champion ceremony on rank changes
 *
 * Phase 5 · 2026-05-13 · Layer 3 (cinematic, no trading touch)
 */
import { useEffect, useMemo, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useTerminalData, selectAgents } from "../lib/useTerminalData.js"
import { useTerminalDeltas, EVENT_TYPE } from "../lib/useTerminalDeltas.js"
import { usePaperArena } from "../lib/usePaperArena.js"
import { calculateXP } from "../phase_x20/economy/XPWallet.js"
import { CASTERS } from "../phase_x20/casters/AICasterSystem.js"
import { FACTIONS } from "../phase_x20/factions/FactionEngine.js"
import { classifyMarketDNA } from "../phase_x20/dna/MarketDNAEngine.js"
import { createAgentMemory } from "../phase_x20/memory/AgentMemoryEngine.js"
import { getCameraMode } from "../phase_x20/director/CinematicDirector.js"

// ── Phase 10: paper-agent normalizer ──────────────────────────────────────
// Maps paper-arena agent schema to the same shape XPLeaderboard expects.
// Adds _paper: true marker so UI can distinguish visually.
function normalizePaperAgents(paperAgents) {
  if (!Array.isArray(paperAgents)) return []
  return paperAgents.map((a) => ({
    id:        `paper:${a.id}`,
    label:     a.label,
    sharpe:    Number(a.sharpe_sim || 0),
    trades:    Number(a.trades || 0),
    win_rate:  Number(a.win_rate || 0),
    pnl:       Number(a.simulated_pnl_usd || 0),
    vDD_pct:   Number(a.vDD_pct_sim || 0),
    disabled:  false,
    _paper:    true,
    _faction:  a.faction,
    _color:    a.color,
    _icon:     a.icon,
    _status:   a.status,
  }))
}

// ── Helpers ────────────────────────────────────────────────────────────────
function eloFromAgent(a) {
  // Visual ELO computed from real Sharpe + trades + win_rate (no real money allocation)
  const base = 1200
  const sharpe = Number(a?.sharpe || 0)
  const trades = Number(a?.trades || 0)
  const wr = Number(a?.win_rate || 0)
  return Math.round(base + sharpe * 200 + trades * 2 + wr * 100)
}

function assignFaction(agentId) {
  // Deterministic faction assignment by id hash
  if (!agentId) return FACTIONS[0]
  let h = 0
  for (const ch of String(agentId)) h = (h * 31 + ch.charCodeAt(0)) & 0xffff
  return FACTIONS[h % FACTIONS.length]
}

function rankIcon(rank) {
  if (rank === 1) return "👑"
  if (rank === 2) return "🥈"
  if (rank === 3) return "🥉"
  return `#${rank}`
}

// Caster phrase banks per personality (Layer 3 cosmetic — derived from real events)
const CASTER_PHRASES = {
  HYPE: {
    [EVENT_TYPE.BTC_BREAKOUT_UP]: (e) => `🔥 EXPLOSION! BTC ripped +${e.move.toFixed(2)}% — sellers DESTROYED at $${e.price.toFixed(0)}!`,
    [EVENT_TYPE.GOD_CANDLE]: (e) => `⚡ GOD CANDLE! ${e.move > 0 ? "+" : ""}${e.move.toFixed(2)}% one-shot move! THE CROWD IS SCREAMING!`,
    [EVENT_TYPE.KILLSWITCH_FIRE]: () => `☠ KILLSWITCH FIRED! It's brutal out there! Capital DOWN!`,
    [EVENT_TYPE.HALT_TRIGGERED]: () => `⛔ GLOBAL HALT! Trading frozen — protection engaged in full!`,
    [EVENT_TYPE.EQUITY_NEW_HIGH]: (e) => `💎 NEW PEAK! $${e.value.toFixed(2)} — UNTOUCHABLE!`,
    [EVENT_TYPE.AGENT_LEAD_CHANGE]: (e) => `⚔ NEW LEADER! ${e.to} OVERTHROWS ${e.from} — the throne shifts!`,
    [EVENT_TYPE.SAFE_MODE_ON]: () => `🛡 SAFE MODE! The defense is locked in!`,
    [EVENT_TYPE.REGIME_FLIP]: (e) => `🌪 REGIME SHIFT! ${e.from} → ${e.to} — everything changes!`,
  },
  TACTIC: {
    [EVENT_TYPE.BTC_BREAKOUT_UP]: (e) => `Trend filter passed at $${e.price.toFixed(0)}, +${e.move.toFixed(2)}% over poll. Watching for follow-through above resistance.`,
    [EVENT_TYPE.GOD_CANDLE]: (e) => `Statistical outlier: ${e.move.toFixed(2)}% in single poll. Volatility regime now elevated; cooling expected.`,
    [EVENT_TYPE.KILLSWITCH_FIRE]: (e) => `Consec loss ${e.count}/${e.max} triggered killswitch. System integrity preserved per protocol.`,
    [EVENT_TYPE.HALT_TRIGGERED]: (e) => `Halt engaged${e.reason ? ": " + String(e.reason).slice(0, 40) : ""}. All trading suspended.`,
    [EVENT_TYPE.EQUITY_NEW_HIGH]: (e) => `Session high: $${e.value.toFixed(2)}. Drawdown reset to zero.`,
    [EVENT_TYPE.AGENT_LEAD_CHANGE]: (e) => `Leaderboard update: ${e.to} now leads at Sharpe ${e.sharpe.toFixed(3)}, surpassing ${e.from}.`,
    [EVENT_TYPE.SAFE_MODE_ON]: () => `Safe mode active. Position sizing reduced per risk governor.`,
    [EVENT_TYPE.REGIME_FLIP]: (e) => `Regime transition: ${e.from} → ${e.to}. Trade thresholds recalibrating.`,
  },
  ORACLE: {
    [EVENT_TYPE.BTC_BREAKOUT_UP]: (e) => `The river flows upward... ${e.price.toFixed(0)} is just a number, but the current is real.`,
    [EVENT_TYPE.GOD_CANDLE]: (e) => `A sudden gift from the void. ${e.move.toFixed(2)}% — fortune favors the patient.`,
    [EVENT_TYPE.KILLSWITCH_FIRE]: () => `The system breathes in. To survive is to endure another cycle.`,
    [EVENT_TYPE.HALT_TRIGGERED]: () => `Silence is wisdom. The arena rests; capital remembers.`,
    [EVENT_TYPE.EQUITY_NEW_HIGH]: (e) => `A new horizon at $${e.value.toFixed(2)}. The ceiling lifts as the trader rises.`,
    [EVENT_TYPE.AGENT_LEAD_CHANGE]: (e) => `The crown moves. ${e.to} carries the weight now — for how long, who can say.`,
    [EVENT_TYPE.SAFE_MODE_ON]: () => `Wisdom whispers caution. The defensive mind survives.`,
    [EVENT_TYPE.REGIME_FLIP]: (e) => `The market changes its face: ${e.from} fades, ${e.to} rises.`,
  },
}

function casterPhrase(personality, event) {
  const bank = CASTER_PHRASES[personality] || {}
  const fn = bank[event.type]
  return fn ? fn(event) : null
}

// ── Sub-components ────────────────────────────────────────────────────────

function XPLeaderboard({ agents }) {
  const rows = useMemo(() => {
    return [...agents]
      .map((a) => ({
        ...a,
        xp: calculateXP(a.trades || 0, a.sharpe || 0),
        elo: eloFromAgent(a),
        faction: a._faction || assignFaction(a.id),
      }))
      .sort((a, b) => b.elo - a.elo)
      .slice(0, 10)  // Phase 10: top 10 (was 8) — accommodates 2 real + 8 paper
  }, [agents])

  return (
    <div className="qwr-panel p-3 space-y-1.5"
         style={{
           background: "rgba(8,15,30,0.75)",
           borderColor: "var(--accent-gold)",
           boxShadow: "0 0 14px -4px var(--accent-gold)",
         }}>
      <div className="flex items-center justify-between mb-2">
        <span className="pk text-[9px] tracking-widest" style={{ color: "var(--accent-gold)" }}>
          👑 LEADERBOARD · ELO + XP
        </span>
        <span className="pk text-[8px] tracking-widest" style={{ color: "var(--text-dim)" }}>
          LIVE · {rows.length}
        </span>
      </div>
      <AnimatePresence initial={false}>
        {rows.map((r, i) => {
          const rank = i + 1
          const color = rank === 1 ? "var(--accent-gold)"
                     : rank === 2 ? "var(--accent-cyan)"
                     : rank === 3 ? "var(--accent-purple)"
                     : "var(--text-dim)"
          return (
            <motion.div
              key={r.id}
              layout
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 8 }}
              transition={{ type: "spring", stiffness: 380, damping: 28 }}
              className="mono text-[10px] flex items-center justify-between px-2 py-1 border-l-2"
              style={{
                borderColor: color,
                background: rank <= 3 ? `${color}11` : "transparent",
                opacity: r._paper ? 0.92 : 1,
              }}
            >
              <span className="flex-shrink-0 w-7 text-[9px] tracking-widest"
                    style={{ color }}>
                {rankIcon(rank)}
              </span>
              <span className="flex-1 truncate flex items-center gap-1">
                {r._paper && (
                  <span className="pk text-[7px] tracking-widest px-1"
                        style={{
                          color: "var(--accent-yellow)",
                          background: "rgba(250,204,21,0.12)",
                          border: "1px solid var(--accent-yellow)",
                          borderRadius: 2,
                        }}>
                    🎮 PAPER
                  </span>
                )}
                <span style={{ color: r._color || color }}>{r.label || `A-${r.id}`}</span>
                <span style={{ color: "var(--text-dim)" }}>· {r.faction}</span>
              </span>
              <span className="flex-shrink-0 text-right" style={{ color: "var(--accent-cyan)" }}>
                ELO {r.elo}
              </span>
              <span className="flex-shrink-0 ml-3" style={{ color: "var(--accent-yellow)" }}>
                XP {r.xp}
              </span>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}

function CasterStream({ events, paperCommentary }) {
  const [lines, setLines] = useState([])
  const seenRef = useRef(new Set())

  useEffect(() => {
    if (!events?.length) return
    const fresh = []
    for (const e of events.slice(0, 6)) {
      if (seenRef.current.has(e.id)) continue
      seenRef.current.add(e.id)
      // Each new event gets a deterministic caster personality
      let hash = 0
      for (const ch of e.id) hash = (hash * 31 + ch.charCodeAt(0)) & 0xffff
      const caster = CASTERS[hash % CASTERS.length]
      const text = casterPhrase(caster.tone || caster.name?.toUpperCase()?.split(" ")[0], e) ||
                   casterPhrase("TACTIC", e)
      if (text) fresh.push({ id: e.id, caster, text, ts: Date.now(), paper: false })
    }
    if (fresh.length > 0) {
      setLines((prev) => [...fresh, ...prev].slice(0, 6))
    }
  }, [events])

  // Phase 10: inject paper commentary as separate stream (deduplicated)
  useEffect(() => {
    if (!paperCommentary?.length) return
    const fresh = []
    for (const c of paperCommentary) {
      const key = `paper:${c.personality}:${c.text.slice(0, 40)}`
      if (seenRef.current.has(key)) continue
      seenRef.current.add(key)
      // wrap to look like a caster line
      fresh.push({
        id: key,
        caster: { name: `PAPER ${c.personality}`, tone: c.personality },
        text: c.text,
        ts: Date.now(),
        paper: true,
      })
    }
    if (fresh.length > 0) {
      setLines((prev) => [...fresh, ...prev].slice(0, 6))
    }
  }, [paperCommentary])

  // TTL: drop lines after 30s
  const [, setT] = useState(0)
  useEffect(() => {
    const i = setInterval(() => {
      setT((v) => v + 1)
      const now = Date.now()
      setLines((prev) => prev.filter((l) => now - l.ts < 32000))
    }, 1000)
    return () => clearInterval(i)
  }, [])

  if (!lines.length) return null

  const casterColor = {
    HYPE:   "var(--accent-pink)",
    TACTIC: "var(--accent-cyan)",
    ORACLE: "var(--accent-purple)",
  }

  return (
    <div className="space-y-1.5">
      <AnimatePresence initial={false}>
        {lines.map((line) => {
          const tone = line.caster.tone || (line.caster.name || "").toUpperCase().split(" ")[0]
          const color = casterColor[tone] || "var(--accent-cyan)"
          // Phase 10: paper-mode caster lines get yellow accent
          const finalColor = line.paper ? "var(--accent-yellow)" : color
          return (
            <motion.div
              key={line.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.25 }}
              className="mono text-[11px] leading-snug px-3 py-1.5 border-l-2"
              style={{
                color: "var(--text)",
                borderColor: finalColor,
                background: line.paper ? "rgba(20,15,5,0.85)" : "rgba(8,15,30,0.78)",
                boxShadow: `inset 0 0 8px ${finalColor}22`,
              }}
            >
              {line.paper && (
                <span className="pk text-[7px] tracking-widest mr-1.5 px-1"
                      style={{
                        color: "var(--accent-yellow)",
                        border: "1px solid var(--accent-yellow)",
                        borderRadius: 2,
                      }}>
                  🎮 PAPER
                </span>
              )}
              <span className="pk text-[8px] tracking-widest mr-2"
                    style={{ color: finalColor, textShadow: `0 0 4px ${finalColor}` }}>
                ◆ {(line.caster.name || tone || "?").toUpperCase()}:
              </span>
              {line.text}
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}

function ChampionCrown({ event }) {
  // Renders a brief crown-transfer animation when AGENT_LEAD_CHANGE fires
  if (!event) return null
  const mode = getCameraMode(event.type)
  const camShake = mode === "SHAKE"
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.6, y: -30 }}
      animate={{
        opacity: 1,
        scale: 1,
        y: 0,
        x: camShake ? [0, -2, 2, -1, 1, 0] : 0,
      }}
      exit={{ opacity: 0, scale: 0.6, y: -30 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="fixed top-24 left-1/2 -translate-x-1/2 px-5 py-3 pk text-[12px] tracking-widest pointer-events-none"
      style={{
        zIndex: 200,
        color: "var(--accent-gold)",
        background: "rgba(8,15,30,0.92)",
        border: "2px solid var(--accent-gold)",
        boxShadow: "0 0 32px -4px var(--accent-gold), inset 0 0 18px rgba(255,215,0,0.25)",
        textShadow: "0 0 12px var(--accent-gold)",
      }}
    >
      👑 NEW CHAMPION: {event.to} 👑
    </motion.div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────
export default function ChampionshipOverlay({
  layout = "right-rail",
  showLeaderboard = true,
  showCasters = true,
  showCrown = true,
}) {
  const { data } = useTerminalData()
  const events = useTerminalDeltas()
  const realAgents = useMemo(() => (data ? selectAgents(data) : []), [data])

  // Phase 10: pull paper agents + commentary
  const { data: paperData, isPaperMode } = usePaperArena()
  const paperAgents = useMemo(
    () => (isPaperMode ? normalizePaperAgents(paperData?.agents) : []),
    [paperData, isPaperMode]
  )
  const paperCommentary = isPaperMode ? (paperData?.commentary || []) : []

  // Merge real + paper for leaderboard
  const allAgents = useMemo(
    () => [...realAgents, ...paperAgents],
    [realAgents, paperAgents]
  )

  // Champion ceremony — show crown for 4s after AGENT_LEAD_CHANGE
  const [crownEvent, setCrownEvent] = useState(null)
  const lastCrownIdRef = useRef(null)
  useEffect(() => {
    const leadChange = events.find((e) => e.type === EVENT_TYPE.AGENT_LEAD_CHANGE)
    if (leadChange && leadChange.id !== lastCrownIdRef.current) {
      lastCrownIdRef.current = leadChange.id
      setCrownEvent(leadChange)
      const t = setTimeout(() => setCrownEvent(null), 4000)
      return () => clearTimeout(t)
    }
  }, [events])

  // Phase 10: paper-arena champion crown — fires when paper #1 changes
  const lastPaperChampionRef = useRef(null)
  useEffect(() => {
    if (!isPaperMode || !paperAgents.length) return
    const sorted = [...paperAgents].sort((a, b) => eloFromAgent(b) - eloFromAgent(a))
    const top = sorted[0]
    if (top && top.label !== lastPaperChampionRef.current) {
      const prevTop = lastPaperChampionRef.current
      lastPaperChampionRef.current = top.label
      // Skip first set (no transition)
      if (prevTop) {
        setCrownEvent({
          id:   `paper-crown-${Date.now()}`,
          type: EVENT_TYPE.AGENT_LEAD_CHANGE,
          to:   `🎮 ${top.label}`,
          from: prevTop,
          sharpe: top.sharpe,
          _paper: true,
        })
        const t = setTimeout(() => setCrownEvent(null), 4000)
        return () => clearTimeout(t)
      }
    }
  }, [paperAgents, isPaperMode])

  if (!allAgents.length) return null

  return (
    <>
      {showCrown && (
        <AnimatePresence>
          {crownEvent && <ChampionCrown event={crownEvent} />}
        </AnimatePresence>
      )}

      <div className={`fixed ${layout === "right-rail" ? "right-4 top-24" : "left-4 top-24"} z-40 w-[320px] space-y-3 pointer-events-none`}>
        {showLeaderboard && (
          <div className="pointer-events-auto">
            <XPLeaderboard agents={allAgents} />
          </div>
        )}
        {showCasters && (
          <div className="pointer-events-auto">
            <CasterStream events={events} paperCommentary={paperCommentary} />
          </div>
        )}
      </div>
    </>
  )
}
