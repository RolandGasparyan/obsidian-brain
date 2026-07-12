import { motion } from "framer-motion"
import InteractiveCard from "./InteractiveCard.jsx"

export default function RegimeGauge({ value }) {
  const pct = Math.max(0, Math.min(1, value))
  const color = pct > 0.75 ? "#00ff41" : pct > 0.5 ? "#ffff00" : "#ff3333"
  const label = pct > 0.75 ? "TRENDING" : pct > 0.5 ? "NEUTRAL" : "WEAK"

  return (
    <InteractiveCard
      title="REGIME STATE"
      tooltip="Composite of ATR expansion, volume z-score, and momentum slope"
      accent={color}
      expanded={
        <div className="space-y-1 mono">
          <div>Strength: {(pct*100).toFixed(1)}%</div>
          <div>Class: {label}</div>
          <div>ATR · Vol · Momentum weighted</div>
        </div>
      }
    >
      <div className="flex flex-col items-center justify-center py-1">
        <motion.div
          className="pk text-[22px]"
          style={{
            color,
            textShadow: pct > 0.75 ? `0 0 12px ${color}` : `0 0 6px ${color}44`,
          }}
          animate={{ opacity: pct > 0.75 ? [1, 0.85, 1] : 1 }}
          transition={{ duration: 1.6, repeat: pct > 0.75 ? Infinity : 0 }}
        >
          {(pct * 100).toFixed(0)}%
        </motion.div>
        <div className="pk text-[7px] text-[color:var(--subdim)] mt-2 tracking-widest">
          {label}
        </div>
        <div className="mt-2 w-full h-1.5 border border-[color:var(--border)] bg-[color:var(--panel)]">
          <motion.div
            className="h-full"
            style={{ background: color, boxShadow: `0 0 6px ${color}` }}
            animate={{ width: `${pct*100}%` }}
            transition={{ duration: 0.8, ease: [0.22,0.61,0.36,1] }}
          />
        </div>
      </div>
    </InteractiveCard>
  )
}
