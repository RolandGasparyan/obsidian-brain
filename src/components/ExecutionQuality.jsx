import NumberTicker from "./NumberTicker.jsx"
import InteractiveCard from "./InteractiveCard.jsx"

export default function ExecutionQuality({ slippage, spread }) {
  return (
    <InteractiveCard
      title="EXEC QUALITY"
      tooltip="Slippage = actual vs expected fill. Spread = bid/ask gap."
      accent="#00ffff"
      expanded={
        <div className="space-y-1 mono">
          <div>Slippage: {slippage.toFixed(3)}%</div>
          <div>Spread:   {spread.toFixed(3)}%</div>
          <div className="text-[color:var(--subdim)]">Target: &lt; 0.05% combined</div>
        </div>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="pk text-[7px] text-[color:var(--subdim)] tracking-widest">SLIPPAGE</div>
          <div className="pk text-[14px] text-[color:var(--cyan)] mt-1" style={{ textShadow: "0 0 6px rgba(0,255,255,0.4)" }}>
            <NumberTicker value={slippage} format={v => v.toFixed(3)+"%"} />
          </div>
        </div>
        <div>
          <div className="pk text-[7px] text-[color:var(--subdim)] tracking-widest">SPREAD</div>
          <div className="pk text-[14px] text-[color:var(--cyan)] mt-1" style={{ textShadow: "0 0 6px rgba(0,255,255,0.4)" }}>
            <NumberTicker value={spread} format={v => v.toFixed(3)+"%"} />
          </div>
        </div>
      </div>
    </InteractiveCard>
  )
}
