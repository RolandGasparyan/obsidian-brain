import { motion } from "framer-motion"
import NumberTicker from "./NumberTicker.jsx"
import InteractiveCard from "./InteractiveCard.jsx"

export default function SurvivalGauge({ probability }) {
  const r = 36
  const C = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(1, probability))
  const color = pct > 0.7 ? "#00ff41" : pct > 0.4 ? "#ffff00" : "#ff3333"

  return (
    <InteractiveCard
      title="SURVIVAL P(SURV)"
      tooltip="Monte Carlo ruin simulation"
      accent={color}
      expanded={
        <div className="space-y-1 mono">
          <div>P(survive N trades): {(pct*100).toFixed(2)}%</div>
          <div>P(ruin): {((1-pct)*100).toFixed(2)}%</div>
          <div className="text-[color:var(--subdim)]">Backed by 10k Monte Carlo paths</div>
        </div>
      }
    >
      <div className="flex items-center gap-3 py-1">
        <svg width="88" height="88" className="-rotate-90 shrink-0">
          <circle cx="44" cy="44" r={r} stroke="var(--border)" strokeWidth="5" fill="none" />
          <motion.circle
            cx="44" cy="44" r={r} stroke={color} strokeWidth="5" fill="none"
            strokeDasharray={C} strokeLinecap="butt"
            initial={{ strokeDashoffset: C }}
            animate={{ strokeDashoffset: C - C*pct }}
            transition={{ duration: 0.9, ease: [0.22,0.61,0.36,1] }}
            style={{ filter: `drop-shadow(0 0 4px ${color})` }}
          />
        </svg>
        <div>
          <div className="pk text-[18px]" style={{ color, textShadow: `0 0 6px ${color}55` }}>
            <NumberTicker value={pct*100} format={v => v.toFixed(1)+"%"} />
          </div>
          <div className="pk text-[7px] text-[color:var(--subdim)] mt-1 tracking-widest">N-TRADE SURV</div>
        </div>
      </div>
    </InteractiveCard>
  )
}
