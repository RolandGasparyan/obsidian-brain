import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import InteractiveCard from "./InteractiveCard.jsx"
import { AGENTS } from "./AgentSprites.jsx"

// Institutional badges for each of the 8 voting agents.
// Pixel-art sprites but embedded in the clean glass aesthetic.
function AgentBadge({ agent, active, confidence }) {
  const { name, role, Sprite, color } = agent
  const [hover, setHover] = useState(false)
  return (
    <motion.div
      onHoverStart={() => setHover(true)}
      onHoverEnd={() => setHover(false)}
      whileHover={{ y: -2 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
      className="relative flex items-center gap-3 p-2.5 rounded-lg border border-white/5 bg-white/[0.02] hover:border-white/10"
      style={{
        boxShadow: active
          ? `0 0 0 1px ${color}55, 0 0 20px -8px ${color}88`
          : undefined,
      }}
    >
      <div
        className="relative w-9 h-9 rounded flex items-center justify-center shrink-0"
        style={{
          background: `linear-gradient(135deg, ${color}22, transparent)`,
          border: `1px solid ${color}33`,
        }}
      >
        <Sprite size={28} color={color} />
        {active && (
          <span
            className="absolute -top-1 -right-1 w-2 h-2 rounded-full"
            style={{ background: color, boxShadow: `0 0 6px ${color}` }}
          />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-semibold tracking-wider" style={{ color }}>
          {name}
        </div>
        <div className="text-[9px] uppercase tracking-[0.15em] text-white/40 truncate">
          {role}
        </div>
        <div className="mt-1 h-0.5 rounded-full bg-white/5 overflow-hidden">
          <motion.div
            className="h-full"
            style={{ background: color }}
            animate={{ width: `${confidence*100}%` }}
            transition={{ duration: 0.6, ease: [0.22,0.61,0.36,1] }}
          />
        </div>
      </div>
      <AnimatePresence>
        {hover && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            className="absolute left-1/2 -translate-x-1/2 -top-8 z-10 px-2 py-1 rounded text-[9px] uppercase tracking-[0.15em] bg-black/90 border border-white/10 whitespace-nowrap pointer-events-none"
            style={{ color }}
          >
            {(confidence*100).toFixed(0)}% conviction
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function AgentCouncil() {
  // Each agent has a fluctuating "conviction" that drifts independently
  const [convictions, setConvictions] = useState(() =>
    AGENTS.reduce((acc, a) => { acc[a.id] = 0.3 + Math.random()*0.5; return acc }, {})
  )
  const [activeId, setActiveId] = useState("alpha")

  useEffect(() => {
    const t = setInterval(() => {
      setConvictions(c => {
        const next = { ...c }
        for (const a of AGENTS) {
          const drift = (Math.random() - 0.5) * 0.12
          next[a.id] = Math.max(0.05, Math.min(1, next[a.id] + drift))
        }
        return next
      })
      // Rotate "active speaker" to whichever has highest conviction
      setConvictions(c => {
        const top = AGENTS.reduce((best, a) => c[a.id] > c[best.id] ? a : best, AGENTS[0])
        setActiveId(top.id)
        return c
      })
    }, 1600)
    return () => clearInterval(t)
  }, [])

  const active = AGENTS.find(a => a.id === activeId)

  return (
    <InteractiveCard
      title="Agent Council · 8 Voters"
      tooltip="Each agent independently votes on the active trade thesis; consensus threshold 3/8"
      expanded={
        <div className="space-y-2">
          <div>Active speaker: <span style={{ color: active?.color }}>{active?.name}</span> — {active?.role}</div>
          <div className="text-white/40">Votes aggregate by weighted conviction. Below threshold ⇒ HOLD.</div>
        </div>
      }
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {AGENTS.map(a => (
          <AgentBadge
            key={a.id}
            agent={a}
            active={a.id === activeId}
            confidence={convictions[a.id]}
          />
        ))}
      </div>
    </InteractiveCard>
  )
}
