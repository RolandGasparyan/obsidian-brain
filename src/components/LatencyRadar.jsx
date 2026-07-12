import { motion } from "framer-motion"
import NumberTicker from "./NumberTicker.jsx"
import InteractiveCard from "./InteractiveCard.jsx"

export default function LatencyRadar({ latencyMs }) {
  const good = latencyMs <= 150
  const warn = latencyMs > 150 && latencyMs <= 300
  const bad  = latencyMs > 300
  const color = good ? "#00ff41" : warn ? "#ffff00" : "#ff3333"
  const pct = Math.min(1, latencyMs / 450)

  return (
    <InteractiveCard
      title="EXEC LATENCY"
      tooltip="End-to-end order roundtrip"
      accent={color}
      expanded={
        <div className="space-y-1 mono">
          <div>Current: {latencyMs.toFixed(0)} ms</div>
          <div>{good ? "✓ Green zone (<150ms)" : warn ? "Amber zone (150-300ms)" : "Red zone (>300ms)"}</div>
        </div>
      }
    >
      <div className="flex items-baseline gap-2">
        <motion.div
          className="pk text-[22px]"
          style={{ color, textShadow: `0 0 6px ${color}66` }}
          animate={{ opacity: bad ? [1, 0.55, 1] : 1 }}
          transition={{ duration: 1.0, repeat: bad ? Infinity : 0 }}
        >
          <NumberTicker value={latencyMs} format={v => Math.round(v).toString()} />
        </motion.div>
        <div className="pk text-[10px] text-[color:var(--subdim)]">MS</div>
      </div>
      <div className="mt-3 h-1.5 border border-[color:var(--border)] bg-[color:var(--panel)]">
        <motion.div
          className="h-full"
          style={{ background: color, boxShadow: `0 0 6px ${color}` }}
          animate={{ width: `${pct*100}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </InteractiveCard>
  )
}
