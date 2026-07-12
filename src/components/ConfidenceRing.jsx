import { motion } from "framer-motion"
import InteractiveCard from "./InteractiveCard.jsx"
import NumberTicker from "./NumberTicker.jsx"

export default function ConfidenceRing({ value }) {
  const pct = Math.max(0, Math.min(1, value))
  const r = 38
  const C = 2 * Math.PI * r
  const color = pct > 0.7 ? "#00ff41" : pct > 0.4 ? "#ffff00" : "#ff3333"

  return (
    <InteractiveCard
      title="CONFIDENCE"
      tooltip="Composite edge signal — WR × 0.4 + Expectancy × 0.4 − DD × 0.2"
      accent={color}
      expanded={
        <div className="space-y-1 mono">
          <div>Score: {(pct*100).toFixed(1)}%</div>
          <div>{pct > 0.7 ? "Strong edge" : pct > 0.4 ? "Moderate" : "Weak / decay"}</div>
        </div>
      }
    >
      <div className="flex items-center gap-4 py-1">
        <div className="relative shrink-0">
          <svg width="96" height="96" className="-rotate-90">
            <circle cx="48" cy="48" r={r} stroke="var(--border)" strokeWidth="5" fill="none" />
            <motion.circle
              cx="48" cy="48" r={r}
              stroke={color} strokeWidth="5" fill="none"
              strokeDasharray={C} strokeLinecap="butt"
              initial={{ strokeDashoffset: C }}
              animate={{ strokeDashoffset: C - C*pct }}
              transition={{ duration: 0.9, ease: [0.22,0.61,0.36,1] }}
              style={{ filter: `drop-shadow(0 0 5px ${color})` }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="pk text-[14px]" style={{ color, textShadow: `0 0 6px ${color}66` }}>
              <NumberTicker value={pct*100} format={v => v.toFixed(0)+"%"} />
            </div>
          </div>
        </div>
        <div>
          <div className="pk text-[7px] text-[color:var(--subdim)] tracking-widest mb-1">MODEL EDGE</div>
          <div className="pk text-[10px]" style={{ color }}>
            {pct > 0.7 ? "STRONG" : pct > 0.4 ? "MODERATE" : "WEAK"}
          </div>
        </div>
      </div>
    </InteractiveCard>
  )
}
