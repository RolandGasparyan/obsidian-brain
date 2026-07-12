/**
 * AgentDetailedStats.jsx — full per-agent stats panel.
 *
 * Renders all 11 fields per operator's vision:
 *   PnL · WinRate · Sharpe · Drawdown · XP · Streak · Position
 *   Regime · Confidence · Exposure · Status
 *
 * Data is REAL from terminal.json. Derived fields are deterministic
 * (no Math.random, no fake numbers).
 *
 * Phase 7 · 2026-05-13 · Layer 3 (visual telemetry display)
 */
import { useEffect, useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useTerminalData, selectAgents } from "../lib/useTerminalData.js"
import { usePaperArena } from "../lib/usePaperArena.js"
import { calculateXP } from "../phase_x20/economy/XPWallet.js"
import { FACTIONS } from "../phase_x20/factions/FactionEngine.js"
import { classifyMarketDNA } from "../phase_x20/dna/MarketDNAEngine.js"

function assignFaction(agent) {
  if (agent && agent._faction) return agent._faction
  const id = agent?.id || agent
  if (!id) return FACTIONS[0]
  let h = 0
  for (const ch of String(id)) h = (h * 31 + ch.charCodeAt(0)) & 0xffff
  return FACTIONS[h % FACTIONS.length]
}

// Phase 10: paper agent normalizer — preserves rich state from paper engine
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
    // Pre-derived stats from the paper engine (richer than terminal.json gives us)
    _paperRich: {
      confidence: a.confidence,
      exposure:   a.exposure_pct,
      xp:         a.xp,
      streak:     a.streak,
      position:   a.position,
      status:     a.status,
      lastAction: a.last_action,
      icon:       a.icon,
      color:      a.color,
      personality: a.personality,
    },
  }))
}

// Derive visual metrics from real fields (cosmetic only, no real capital allocation)
function deriveStats(agent, terminalData) {
  const sharpe   = Number(agent?.sharpe || 0)
  const pnl      = Number(agent?.pnl || 0)
  const trades   = Number(agent?.trades || 0)
  const wr       = Number(agent?.win_rate || 0)
  const dd       = Number(agent?.vDD_pct || 0)
  const disabled = Boolean(agent?.disabled)

  // Phase 10: paper agents bring their own rich state — use it directly
  if (agent?._paper && agent._paperRich) {
    const r = agent._paperRich
    return {
      sharpe, pnl, trades, wr, dd,
      confidence: r.confidence,
      streak:     r.streak,
      position:   r.position,
      exposure:   r.exposure,
      status:     r.status,
      regime:     terminalData?.bot?.regime || "CHOP",
      xp:         r.xp,
      faction:    assignFaction(agent),
      disabled:   false,
      isPaper:    true,
      lastAction: r.lastAction,
      icon:       r.icon,
      personality: r.personality,
    }
  }

  // Confidence = sharpe normalized to 0-100 (cosmetic)
  const confidence = Math.max(0, Math.min(100, 50 + sharpe * 40))

  // Streak = derived from win rate × trades (cosmetic estimate)
  const streak = Math.floor(wr * Math.max(0, trades) * 0.6)

  // Position = if recent pnl != 0 then "open", else "flat"
  // (we don't have real position data per agent in terminal.json so we approximate)
  const position = pnl !== 0 ? (pnl > 0 ? "LONG" : "SHORT") : "FLAT"

  // Exposure = visual estimate from |pnl| / typical_bucket
  const vbucket = Number(agent?.vbucket || 200)
  const exposure = Math.min(100, Math.abs(pnl) / vbucket * 100)

  // Status badge
  let status = "READY"
  if (disabled) status = "OFFLINE"
  else if (dd >= 10) status = "DEFENSIVE"
  else if (sharpe >= 0.5) status = "STRIKING"
  else if (trades >= 1) status = "ACTIVE"

  const regime = terminalData?.bot?.regime || "CHOP"
  const xp = calculateXP(trades, sharpe)
  const faction = assignFaction(agent)

  return {
    sharpe, pnl, trades, wr, dd,
    confidence, streak, position, exposure, status,
    regime, xp, faction, disabled, isPaper: false,
  }
}

function StatusBadge({ status }) {
  const map = {
    OFFLINE:   { color: "var(--accent-red)",    icon: "💀" },
    DEFENSIVE: { color: "var(--accent-orange)", icon: "🛡" },
    STRIKING:  { color: "var(--accent-green)",  icon: "⚔" },
    ACTIVE:    { color: "var(--accent-cyan)",   icon: "●" },
    READY:     { color: "var(--text-dim)",      icon: "◯" },
  }
  const cfg = map[status] || map.READY
  return (
    <span className="pk text-[8px] tracking-widest"
          style={{
            color: cfg.color,
            textShadow: `0 0 4px ${cfg.color}66`,
          }}>
      {cfg.icon} {status}
    </span>
  )
}

function PositionPill({ position }) {
  const color = position === "LONG"  ? "var(--accent-green)"
              : position === "SHORT" ? "var(--accent-pink)"
              :                        "var(--text-dim)"
  return (
    <span className="pk text-[8px] tracking-widest px-1.5 py-0.5 border"
          style={{
            color,
            borderColor: color,
            background: `${color}11`,
          }}>
      {position}
    </span>
  )
}

function MicroBar({ value, max = 100, color = "var(--accent-cyan)", label }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className="mono text-[9px]">
      {label && (
        <div className="flex justify-between mb-0.5">
          <span style={{ color: "var(--text-dim)" }}>{label}</span>
          <span style={{ color }}>{value.toFixed(1)}</span>
        </div>
      )}
      <div className="h-1 rounded-sm overflow-hidden"
           style={{ background: "rgba(40,40,60,0.6)" }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          style={{
            background: `linear-gradient(90deg, ${color}, ${color}44)`,
            height: "100%",
            boxShadow: `0 0 6px ${color}66`,
          }}
        />
      </div>
    </div>
  )
}

function AgentCard({ agent, stats, expanded, onToggle }) {
  const factionColor = {
    VOID:    "var(--accent-purple)",
    PHOENIX: "var(--accent-orange)",
    TITAN:   "var(--accent-gold)",
    AEGIS:   "var(--accent-green)",
  }[stats.faction] || "var(--text)"

  return (
    <motion.div
      layout
      className="qwr-panel mono text-[10px] overflow-hidden"
      style={{
        background: "rgba(8,15,30,0.78)",
        borderColor: `${factionColor}66`,
        boxShadow: stats.disabled
          ? "0 0 8px -4px var(--accent-red)"
          : `0 0 10px -4px ${factionColor}`,
        opacity: stats.disabled ? 0.55 : 1,
      }}
    >
      <button
        type="button"
        onClick={onToggle}
        className="w-full px-2.5 py-1.5 flex items-center justify-between min-h-touch-sm"
        style={{ cursor: "pointer" }}
      >
        <div className="flex items-center gap-1.5 min-w-0">
          {stats.isPaper && (
            <span className="pk text-[7px] tracking-widest px-1"
                  style={{
                    color: "var(--accent-yellow)",
                    border: "1px solid var(--accent-yellow)",
                    borderRadius: 2,
                    flexShrink: 0,
                  }}>
              🎮
            </span>
          )}
          <span className="pk text-[9px] tracking-widest truncate"
                style={{ color: factionColor }}>
            {agent.label || `A-${agent.id}`}
          </span>
          <span className="pk text-[8px] tracking-widest"
                style={{ color: "var(--text-dim)", flexShrink: 0 }}>
            {stats.faction}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <PositionPill position={stats.position} />
          <StatusBadge status={stats.status} />
        </div>
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="px-2.5 pb-2 pt-1 space-y-1.5"
                 style={{ borderTop: "1px dashed var(--border)" }}>

              {/* Grid: 4 numerical fields */}
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[9px]">
                <div>
                  <span style={{ color: "var(--text-dim)" }}>PnL </span>
                  <span style={{ color: stats.pnl >= 0 ? "var(--accent-green)" : "var(--accent-pink)" }}>
                    {stats.pnl >= 0 ? "+" : ""}${stats.pnl.toFixed(2)}
                  </span>
                </div>
                <div>
                  <span style={{ color: "var(--text-dim)" }}>Sharpe </span>
                  <span style={{ color: stats.sharpe >= 0 ? "var(--accent-green)" : "var(--accent-pink)" }}>
                    {stats.sharpe.toFixed(3)}
                  </span>
                </div>
                <div>
                  <span style={{ color: "var(--text-dim)" }}>WR </span>
                  <span style={{ color: "var(--accent-cyan)" }}>
                    {(stats.wr * 100).toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span style={{ color: "var(--text-dim)" }}>DD </span>
                  <span style={{ color: stats.dd < 5 ? "var(--accent-green)" : stats.dd < 15 ? "var(--accent-orange)" : "var(--accent-red)" }}>
                    {stats.dd.toFixed(2)}%
                  </span>
                </div>
                <div>
                  <span style={{ color: "var(--text-dim)" }}>Trades </span>
                  <span style={{ color: "var(--text)" }}>{stats.trades}</span>
                </div>
                <div>
                  <span style={{ color: "var(--text-dim)" }}>Streak </span>
                  <span style={{ color: "var(--accent-yellow)" }}>{stats.streak}</span>
                </div>
                <div>
                  <span style={{ color: "var(--text-dim)" }}>XP </span>
                  <span style={{ color: "var(--accent-gold)" }}>{stats.xp}</span>
                </div>
                <div>
                  <span style={{ color: "var(--text-dim)" }}>Regime </span>
                  <span style={{ color: "var(--accent-purple)" }}>{stats.regime}</span>
                </div>
              </div>

              {/* Two micro-bars */}
              <div className="space-y-1">
                <MicroBar
                  value={stats.confidence}
                  max={100}
                  color="var(--accent-cyan)"
                  label="Confidence"
                />
                <MicroBar
                  value={stats.exposure}
                  max={100}
                  color="var(--accent-orange)"
                  label="Exposure"
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────
export default function AgentDetailedStats({
  position = "left-rail",
  defaultExpanded = false,
}) {
  const { data } = useTerminalData()
  const { data: paperData, isPaperMode } = usePaperArena()
  const realAgents = useMemo(() => (data ? selectAgents(data) : []), [data])
  const paperAgents = useMemo(
    () => (isPaperMode ? normalizePaperAgents(paperData?.agents) : []),
    [paperData, isPaperMode]
  )
  // Phase 10: combined set — real first, then paper agents
  const agents = useMemo(() => [...realAgents, ...paperAgents], [realAgents, paperAgents])
  const [expandedIds, setExpandedIds] = useState(() => new Set())

  const toggle = (id) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (!agents.length) return null

  const posClass = {
    "left-rail":    "left-4 top-24",
    "right-rail":   "right-4 top-24",
    "bottom-left":  "bottom-4 left-4",
    "bottom-right": "bottom-4 right-4",
  }[position] || "left-4 top-24"

  return (
    <div className={`fixed ${posClass} z-30 w-[300px] space-y-1.5 pointer-events-none`}
         style={{ maxHeight: "calc(100vh - 120px)", overflowY: "auto" }}>
      <div className="pointer-events-none">
        <div className="qwr-panel px-2 py-1.5 mb-1.5 pointer-events-auto"
             style={{
               background: "rgba(8,15,30,0.85)",
               borderColor: "var(--accent-cyan)",
             }}>
          <div className="pk text-[9px] tracking-widest flex justify-between items-center"
               style={{ color: "var(--accent-cyan)" }}>
            <span>🧠 AGENT TELEMETRY</span>
            <span style={{ color: "var(--text-dim)" }}>
              ×{agents.length}
              {paperAgents.length > 0 && (
                <span style={{ color: "var(--accent-yellow)" }}>
                  {" "}({paperAgents.length} 🎮)
                </span>
              )}
            </span>
          </div>
        </div>
      </div>
      {agents.map((a) => {
        const stats = deriveStats(a, data)
        return (
          <div key={a.id} className="pointer-events-auto">
            <AgentCard
              agent={a}
              stats={stats}
              expanded={expandedIds.has(a.id) || defaultExpanded}
              onToggle={() => toggle(a.id)}
            />
          </div>
        )
      })}
    </div>
  )
}
