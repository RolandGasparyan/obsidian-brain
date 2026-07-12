import NumberTicker from "./NumberTicker.jsx"
import InteractiveCard from "./InteractiveCard.jsx"

export default function CapitalCountdown({ balance }) {
  const target = 1000000
  const remaining = Math.max(0, target - balance)
  const progress  = Math.min(1, balance / target)

  return (
    <InteractiveCard
      title="CAPITAL TARGET"
      tooltip="Distance to $1M milestone"
      accent="#00ff41"
      expanded={
        <div className="space-y-1 mono">
          <div>Balance: <NumberTicker value={balance} format={v => "$"+v.toFixed(2)} /></div>
          <div>Target:  ${target.toLocaleString()}</div>
          <div>Progress: {(progress*100).toFixed(3)}%</div>
        </div>
      }
    >
      <div className="pk text-[18px] text-[color:var(--green)]" style={{ textShadow: "0 0 8px rgba(0,255,65,0.5)" }}>
        {remaining > 0
          ? <>$<NumberTicker value={remaining} /></>
          : <span>TARGET HIT</span>}
      </div>
      <div className="mt-3 h-1.5 border border-[color:var(--border)] bg-[color:var(--panel)]">
        <div
          className="h-full"
          style={{
            width: `${progress*100}%`,
            background: "var(--green)",
            boxShadow: "0 0 6px var(--green)",
            transition: "width 0.6s cubic-bezier(0.22,0.61,0.36,1)",
          }}
        />
      </div>
    </InteractiveCard>
  )
}
