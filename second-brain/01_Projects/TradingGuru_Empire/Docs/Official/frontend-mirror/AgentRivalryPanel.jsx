/**
 * AgentRivalryPanel.jsx — visual rivalry tracker between agents.
 *
 * Computes head-to-head matchups from real terminal.json agents[]
 * (sharpe + pnl + win_rate deltas). Tracks faction wars.
 *
 * Phase 6 · 2026-05-13 · Layer 3 (visual narrative, no trading touch)
 */
import { useEffect, useMemo, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useTerminalData, selectAgents } from "../lib/useTerminalData.js"
import { usePaperArena } from "../lib/usePaperArena.js"
import { FACTIONS } from "../phase_x20/factions/FactionEngine.js"
import { createAgentMemory } from "../phase_x20/memory/AgentMemoryEngine.js"

// Phase 10: paper agent normalizer — paper agents carry _faction directly,
// so we prefer that over hash-derived faction.
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
  }))
}

function assignFaction(agent) {
  // Phase 10: paper agents carry _faction directly
  if (agent && agent._faction) return agent._faction
  const id = agent?.id || agent
  if (!id) return FACTIONS[0]
  let h = 0
  for (const ch of String(id)) h = (h * 31 + ch.charCodeAt(0)) & 0xffff
  return FACTIONS[h % FACTIONS.length]
}

const FACTION_COLOR = {
  VOID:    "var(--accent-purple)",
  PHOENIX: "var(--accent-orange)",
  TITAN:   "var(--accent-gold)",
  AEGIS:   "var(--accent-green)",
}

// ── Rivalry detection ─────────────────────────────────────────────────────
// "Rivalry" = two agents with high sharpe difference (close competitors)
// or two agents from same faction with diverging performance
function detectRivalries(agents) {
  if (!agents || agents.length < 2) return []
  const sorted = [...agents].sort((a, b) => (b.sharpe || 0) - (a.sharpe || 0))
  const rivalries = []

  // Top-tier rivalry: #1 vs #2 by sharpe
  if (sorted.length >= 2) {
    const a = sorted[0], b = sorted[1]
    rivalries.push({
      id: `top-${a.id}-${b.id}`,
      type: "TITLE",
      a: a, b: b,
      delta: (a.sharpe || 0) - (b.sharpe || 0),
    })
  }

  // Same-faction rivalry: agents in same faction with biggest performance gap
  const byFaction = {}
  for (const a of agents) {
    const f = assignFaction(a)
    if (!byFaction[f]) byFaction[f] = []
    byFaction[f].push(a)
  }
  for (const [faction, members] of Object.entries(byFaction)) {
    if (members.length < 2) continue
    const sortedMembers = [...members].sort((a, b) => (b.sharpe || 0) - (a.sharpe || 0))
    const top = sortedMembers[0]
    const bottom = sortedMembers[sortedMembers.length - 1]
    if ((top.sharpe || 0) - (bottom.sharpe || 0) >= 0.2) {
      rivalries.push({
        id: `faction-${faction}-${top.id}-${bottom.id}`,
        type: "FACTION",
        faction,
        a: top, b: bottom,
        delta: (top.sharpe || 0) - (bottom.sharpe || 0),
      })
    }
  }

  return rivalries.slice(0, 3)
}

// ── Faction war computation ───────────────────────────────────────────────
function computeFactionWar(agents) {
  const factionStats = FACTIONS.reduce((acc, f) => {
    acc[f] = { name: f, totalSharpe: 0, totalPnl: 0, count: 0 }
    return acc
  }, {})

  for (const a of agents) {
    const f = assignFaction(a)
    if (!factionStats[f]) continue
    factionStats[f].totalSharpe += Number(a.sharpe || 0)
    factionStats[f].totalPnl += Number(a.pnl || 0)
    factionStats[f].count++
  }

  return Object.values(factionStats)
    .filter(f => f.count > 0)
    .map(f => ({
      ...f,
      avgSharpe: f.totalSharpe / f.count,
      avgPnl: f.totalPnl / f.count,
    }))
    .sort((a, b) => b.avgSharpe - a.avgSharpe)
}

// ── Sub-components ────────────────────────────────────────────────────────

function RivalryRow({ rivalry }) {
  const factionA = assignFaction(rivalry.a)
  const factionB = assignFaction(rivalry.b)
  const colorA = FACTION_COLOR[factionA]
  const colorB = FACTION_COLOR[factionB]
  const isPaper = rivalry.a._paper || rivalry.b._paper
  const sharpeA = Number(rivalry.a.sharpe || 0)
  const sharpeB = Number(rivalry.b.sharpe || 0)
  const dominance = Math.abs(rivalry.delta)
  const isClose = dominance < 0.3

  return (
    <motion.div
      layout
      className="mono text-[10px] p-2"
      style={{
        background: "rgba(8,15,30,0.7)",
        border: `1px solid ${isClose ? "var(--accent-yellow)" : colorA}55`,
        borderRadius: 4,
      }}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className="pk text-[8px] tracking-widest flex items-center gap-1.5"
              style={{ color: rivalry.type === "TITLE" ? "var(--accent-gold)" : "var(--accent-cyan)" }}>
          {isPaper && (
            <span className="pk text-[7px] px-1"
                  style={{
                    color: "var(--accent-yellow)",
                    border: "1px solid var(--accent-yellow)",
                    borderRadius: 2,
                  }}>
              🎮 PAPER
            </span>
          )}
          {rivalry.type === "TITLE" ? "⚔ TITLE FIGHT" : `◆ ${rivalry.faction} CIVIL WAR`}
        </span>
        {isClose && (
          <motion.span
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ duration: 0.9, repeat: Infinity }}
            className="pk text-[8px] tracking-widest"
            style={{ color: "var(--accent-yellow)" }}
          >
            🔥 CLOSE
          </motion.span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <div className="flex-1 text-right">
          <div style={{ color: colorA, fontWeight: 600 }}>{rivalry.a.label || `A-${rivalry.a.id}`}</div>
          <div style={{ color: "var(--text-dim)", fontSize: 9 }}>
            S {sharpeA.toFixed(3)} · P ${Number(rivalry.a.pnl || 0).toFixed(2)}
          </div>
        </div>
        <div className="pk text-[9px] tracking-widest" style={{ color: "var(--text)" }}>
          VS
        </div>
        <div className="flex-1 text-left">
          <div style={{ color: colorB, fontWeight: 600 }}>{rivalry.b.label || `A-${rivalry.b.id}`}</div>
          <div style={{ color: "var(--text-dim)", fontSize: 9 }}>
            S {sharpeB.toFixed(3)} · P ${Number(rivalry.b.pnl || 0).toFixed(2)}
          </div>
        </div>
      </div>

      {/* Dominance bar */}
      <div className="mt-1.5 flex h-1 rounded-sm overflow-hidden"
           style={{ background: "rgba(40,40,60,0.6)" }}>
        <motion.div
          initial={{ width: "50%" }}
          animate={{
            width: `${50 + (rivalry.delta * 100)}%`,
          }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          style={{
            background: `linear-gradient(90deg, ${colorA}, ${colorA}66)`,
            height: "100%",
          }}
        />
      </div>
    </motion.div>
  )
}

function FactionWarPanel({ factionWar }) {
  if (!factionWar?.length) return null
  const topPnl = Math.max(1, ...factionWar.map(f => Math.abs(f.totalPnl)))

  return (
    <div className="qwr-panel p-3"
         style={{
           background: "rgba(8,15,30,0.7)",
           borderColor: "var(--accent-purple)",
           boxShadow: "0 0 12px -4px rgba(204,68,255,0.5)",
         }}>
      <div className="pk text-[9px] tracking-widest mb-2"
           style={{ color: "var(--accent-purple)" }}>
        ⚔ FACTION WAR · LIVE
      </div>
      <div className="space-y-1.5">
        {factionWar.map((f, idx) => {
          const color = FACTION_COLOR[f.name] || "var(--text)"
          const dominanceWidth = (Math.abs(f.totalPnl) / topPnl) * 100
          const isLeading = idx === 0
          return (
            <motion.div
              key={f.name}
              layout
              className="mono text-[10px]"
              transition={{ type: "spring", stiffness: 380, damping: 28 }}
            >
              <div className="flex items-center justify-between mb-0.5">
                <span className="flex items-center gap-1.5">
                  {isLeading && <span style={{ color: "var(--accent-gold)" }}>👑</span>}
                  <span style={{ color, fontWeight: 600 }}>{f.name}</span>
                  <span style={{ color: "var(--text-dim)", fontSize: 9 }}>
                    × {f.count}
                  </span>
                </span>
                <span style={{ color: f.totalPnl >= 0 ? "var(--accent-green)" : "var(--accent-pink)" }}>
                  {f.totalPnl >= 0 ? "+" : ""}${f.totalPnl.toFixed(2)}
                </span>
              </div>
              <div className="h-1 rounded-sm overflow-hidden"
                   style={{ background: "rgba(40,40,60,0.6)" }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${dominanceWidth}%` }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                  style={{
                    background: `linear-gradient(90deg, ${color}, ${color}33)`,
                    height: "100%",
                    boxShadow: `0 0 8px ${color}88`,
                  }}
                />
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────
export default function AgentRivalryPanel({ position = "bottom-right" }) {
  const { data } = useTerminalData()
  const { data: paperData, isPaperMode } = usePaperArena()

  const realAgents = useMemo(() => (data ? selectAgents(data) : []), [data])
  const paperAgents = useMemo(
    () => (isPaperMode ? normalizePaperAgents(paperData?.agents) : []),
    [paperData, isPaperMode]
  )
  // Phase 10: detect rivalries on combined set (real + paper). Faction war
  // aggregates both real and paper contributions per faction.
  const agents = useMemo(() => [...realAgents, ...paperAgents], [realAgents, paperAgents])
  const rivalries = useMemo(() => detectRivalries(agents), [agents])
  const factionWar = useMemo(() => computeFactionWar(agents), [agents])

  if (!agents.length) return null

  const posClass = {
    "bottom-right": "bottom-4 right-4",
    "bottom-left":  "bottom-4 left-4",
    "top-right":    "top-24 right-4",
    "top-left":     "top-24 left-4",
  }[position] || "bottom-4 right-4"

  return (
    <div className={`fixed ${posClass} z-40 w-[320px] space-y-2 pointer-events-none`}>
      <div className="pointer-events-auto">
        <FactionWarPanel factionWar={factionWar} />
      </div>
      <div className="pointer-events-auto space-y-1.5">
        <AnimatePresence>
          {rivalries.map((r) => (
            <RivalryRow key={r.id} rivalry={r} />
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
