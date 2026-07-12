/**
 * ChampionshipCyclePanel.jsx — hourly/daily/weekly championship cycle UI.
 *
 * Real cycle countdowns + winner snapshots per cycle window.
 * Titles per operator vision: Sharpe King, Momentum Predator, Survival Champion,
 *                             Volatility Emperor, Recovery Master, Arena Legend.
 *
 * Phase 8 · 2026-05-13 · Layer 3 (visual cycle ceremony, no trading touch)
 */
import { useEffect, useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useTerminalData, selectAgents } from "../lib/useTerminalData.js"
import { usePaperArena } from "../lib/usePaperArena.js"
import { calculateXP } from "../phase_x20/economy/XPWallet.js"

// Phase 10: normalize paper agents to the shape computeTitles() expects.
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
  }))
}

// ── Cycle math ────────────────────────────────────────────────────────────
function secondsUntilNextHour() {
  const now = new Date()
  const next = new Date(now)
  next.setUTCMinutes(0, 0, 0)
  next.setUTCHours(now.getUTCHours() + 1)
  return Math.floor((next - now) / 1000)
}

function secondsUntilNextUTCDay() {
  const now = new Date()
  const next = new Date(now)
  next.setUTCHours(0, 0, 0, 0)
  next.setUTCDate(next.getUTCDate() + 1)
  return Math.floor((next - now) / 1000)
}

function secondsUntilNextMonday() {
  const now = new Date()
  const dow = now.getUTCDay() // 0 = Sunday, 1 = Monday
  const daysUntilMonday = (8 - dow) % 7 || 7
  const next = new Date(now)
  next.setUTCHours(0, 0, 0, 0)
  next.setUTCDate(next.getUTCDate() + daysUntilMonday)
  return Math.floor((next - now) / 1000)
}

function formatCountdown(seconds) {
  if (seconds <= 0) return "00:00:00"
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}

// ── Title computation per cycle ───────────────────────────────────────────
function computeTitles(agents) {
  if (!agents.length) return []
  const enriched = agents.map(a => ({
    ...a,
    sharpe: Number(a.sharpe || 0),
    pnl: Number(a.pnl || 0),
    trades: Number(a.trades || 0),
    wr: Number(a.win_rate || 0),
    dd: Number(a.vDD_pct || 0),
    xp: calculateXP(a.trades || 0, a.sharpe || 0),
    disabled: Boolean(a.disabled),
  }))

  const active = enriched.filter(a => !a.disabled)
  if (!active.length) return []

  // Sharpe King — highest sharpe
  const sharpeKing = [...active].sort((a, b) => b.sharpe - a.sharpe)[0]

  // Momentum Predator — highest trades (most active)
  const momentumPredator = [...active].sort((a, b) => b.trades - a.trades)[0]

  // Survival Champion — lowest DD with at least 1 trade (preserved capital best)
  const survivors = active.filter(a => a.trades >= 1)
  const survivalChampion = survivors.length
    ? [...survivors].sort((a, b) => a.dd - b.dd)[0]
    : null

  // Volatility Emperor — highest pnl absolute value (rode the most volatility)
  const volatilityEmperor = [...active].sort((a, b) => Math.abs(b.pnl) - Math.abs(a.pnl))[0]

  // Recovery Master — agents with vDD then recovered (proxy: low DD + positive PnL)
  const recoveryMaster = [...active]
    .filter(a => a.pnl > 0)
    .sort((a, b) => (a.dd + (-b.pnl)) - (b.dd + (-a.pnl)))[0]

  // Arena Legend — highest XP (composite of trades × sharpe)
  const arenaLegend = [...active].sort((a, b) => b.xp - a.xp)[0]

  return [
    { title: "SHARPE KING",        agent: sharpeKing,        metric: `S ${sharpeKing.sharpe.toFixed(3)}`,    color: "var(--accent-gold)",    icon: "👑", paper: !!sharpeKing._paper },
    { title: "MOMENTUM PREDATOR",  agent: momentumPredator,  metric: `${momentumPredator.trades} trades`,    color: "var(--accent-pink)",    icon: "⚡", paper: !!momentumPredator._paper },
    { title: "SURVIVAL CHAMPION",  agent: survivalChampion,  metric: survivalChampion ? `DD ${survivalChampion.dd.toFixed(2)}%` : "—", color: "var(--accent-green)",   icon: "🛡", paper: !!survivalChampion?._paper },
    { title: "VOLATILITY EMPEROR", agent: volatilityEmperor, metric: `$${volatilityEmperor.pnl.toFixed(2)}`, color: "var(--accent-orange)",  icon: "🌪", paper: !!volatilityEmperor._paper },
    { title: "RECOVERY MASTER",    agent: recoveryMaster,    metric: recoveryMaster ? `+$${recoveryMaster.pnl.toFixed(2)}` : "—",     color: "var(--accent-cyan)",    icon: "🔄", paper: !!recoveryMaster?._paper },
    { title: "ARENA LEGEND",       agent: arenaLegend,       metric: `XP ${arenaLegend.xp}`,                 color: "var(--accent-purple)",  icon: "🏆", paper: !!arenaLegend._paper },
  ].filter(t => t.agent)
}

// ── Cycle countdown bar ───────────────────────────────────────────────────
function CycleBar({ label, secondsTotal, secondsLeft, color }) {
  const pct = Math.max(0, Math.min(100, (1 - secondsLeft / secondsTotal) * 100))
  return (
    <div className="mono text-[10px]">
      <div className="flex justify-between mb-0.5">
        <span style={{ color }}>{label}</span>
        <span style={{ color: "var(--text-dim)" }}>{formatCountdown(secondsLeft)}</span>
      </div>
      <div className="h-1 rounded-sm overflow-hidden"
           style={{ background: "rgba(40,40,60,0.6)" }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: "linear" }}
          style={{
            background: `linear-gradient(90deg, ${color}, ${color}55)`,
            height: "100%",
            boxShadow: `0 0 6px ${color}`,
          }}
        />
      </div>
    </div>
  )
}

// ── Title card ────────────────────────────────────────────────────────────
function TitleCard({ title }) {
  return (
    <motion.div
      layout
      className="mono text-[10px] p-2 flex items-center justify-between"
      style={{
        background: "rgba(8,15,30,0.78)",
        borderLeft: `3px solid ${title.color}`,
        borderRadius: 3,
        boxShadow: `inset 0 0 12px ${title.color}11`,
      }}
    >
      <div className="flex items-center gap-2 min-w-0">
        <span style={{ fontSize: 14 }}>{title.icon}</span>
        <div className="min-w-0">
          <div className="pk text-[8px] tracking-widest truncate flex items-center gap-1"
               style={{ color: title.color }}>
            {title.paper && (
              <span className="pk text-[7px] px-1"
                    style={{
                      color: "var(--accent-yellow)",
                      border: "1px solid var(--accent-yellow)",
                      borderRadius: 2,
                      flexShrink: 0,
                    }}>
                🎮
              </span>
            )}
            <span className="truncate">{title.title}</span>
          </div>
          <div className="truncate" style={{ color: "var(--text)" }}>
            {title.agent.label || `A-${title.agent.id}`}
          </div>
        </div>
      </div>
      <div className="text-right flex-shrink-0 ml-2">
        <div className="pk text-[8px] tracking-widest"
             style={{ color: title.color }}>
          {title.metric}
        </div>
      </div>
    </motion.div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────
export default function ChampionshipCyclePanel({ position = "bottom-center" }) {
  const { data } = useTerminalData()
  const { data: paperData, isPaperMode } = usePaperArena()
  const realAgents = useMemo(() => (data ? selectAgents(data) : []), [data])
  const paperAgents = useMemo(
    () => (isPaperMode ? normalizePaperAgents(paperData?.agents) : []),
    [paperData, isPaperMode]
  )
  // Phase 10: titles computed from combined pool — paper champions can hold titles
  const agents = useMemo(() => [...realAgents, ...paperAgents], [realAgents, paperAgents])
  const titles = useMemo(() => computeTitles(agents), [agents])

  // Cycle countdowns (re-tick every second)
  const [hourLeft, setHourLeft] = useState(secondsUntilNextHour)
  const [dayLeft, setDayLeft] = useState(secondsUntilNextUTCDay)
  const [weekLeft, setWeekLeft] = useState(secondsUntilNextMonday)

  useEffect(() => {
    const i = setInterval(() => {
      setHourLeft(secondsUntilNextHour())
      setDayLeft(secondsUntilNextUTCDay())
      setWeekLeft(secondsUntilNextMonday())
    }, 1000)
    return () => clearInterval(i)
  }, [])

  if (!agents.length) return null

  const posClass = {
    "bottom-center": "bottom-4 left-1/2 -translate-x-1/2",
    "bottom-left":   "bottom-4 left-4",
    "bottom-right":  "bottom-4 right-4",
  }[position] || "bottom-4 left-1/2 -translate-x-1/2"

  return (
    <div className={`fixed ${posClass} z-30 w-[640px] max-w-[92vw] pointer-events-none`}>
      <div className="qwr-panel p-2.5 pointer-events-auto"
           style={{
             background: "rgba(8,15,30,0.88)",
             borderColor: "var(--accent-gold)",
             boxShadow: "0 0 16px -4px var(--accent-gold), inset 0 0 18px rgba(255,215,0,0.10)",
           }}>
        <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-3">
          {/* Left column: cycle countdowns */}
          <div className="space-y-1.5">
            <div className="pk text-[9px] tracking-widest mb-1"
                 style={{ color: "var(--accent-gold)" }}>
              🏆 CYCLES
            </div>
            <CycleBar label="HOURLY"  secondsTotal={3600}      secondsLeft={hourLeft}  color="var(--accent-cyan)" />
            <CycleBar label="DAILY"   secondsTotal={86400}     secondsLeft={dayLeft}   color="var(--accent-yellow)" />
            <CycleBar label="WEEKLY"  secondsTotal={604800}    secondsLeft={weekLeft}  color="var(--accent-purple)" />
          </div>

          {/* Right column: titles grid */}
          <div>
            <div className="pk text-[9px] tracking-widest mb-1"
                 style={{ color: "var(--accent-gold)" }}>
              👑 CURRENT TITLE HOLDERS
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-1.5">
              <AnimatePresence>
                {titles.map((t) => (
                  <TitleCard key={t.title} title={t} />
                ))}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
