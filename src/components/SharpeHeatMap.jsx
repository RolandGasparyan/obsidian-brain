import { motion } from "framer-motion"
import NumberTicker from "./NumberTicker.jsx"
import InteractiveCard from "./InteractiveCard.jsx"

export default function SharpeHeatMap({ sharpe }) {
  const color = sharpe > 2 ? "#00ff41" : sharpe > 1 ? "#ffff00" : "#ff3333"
  const pct = Math.max(0, Math.min(1, sharpe / 3))

  return (
    <InteractiveCard
      title="SHARPE RATIO"
      tooltip="Annualized risk-adjusted return"
      accent={color}
      expanded={
        <div className="space-y-1 mono">
          <div>Sharpe: {sharpe.toFixed(2)}</div>
          <div>Zone: {sharpe > 2 ? "Institutional" : sharpe > 1 ? "Retail-competitive" : "Sub-viable"}</div>
          <div>Benchmark: 1.5+ for prop desks</div>
        </div>
      }
    >
      <div className="h-2 border border-[color:var(--border)] bg-[color:var(--panel)]">
        <motion.div
          className="h-full"
          style={{ background: color, boxShadow: `0 0 6px ${color}` }}
          animate={{ width: `${pct*100}%` }}
          transition={{ duration: 0.7, ease: [0.22,0.61,0.36,1] }}
        />
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <div className="pk text-[16px]" style={{ color, textShadow: `0 0 6px ${color}55` }}>
          <NumberTicker value={sharpe} format={v => v.toFixed(2)} />
        </div>
        <div className="pk text-[8px] text-[color:var(--subdim)]">SHARPE</div>
      </div>
    </InteractiveCard>
  )
}
