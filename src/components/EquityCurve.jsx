import { AreaChart, Area, ResponsiveContainer, Tooltip, YAxis, XAxis, ReferenceLine } from "recharts"
import InteractiveCard from "./InteractiveCard.jsx"
import NumberTicker from "./NumberTicker.jsx"

export default function EquityCurve({ data, pnl, peak }) {
  const last = data[data.length - 1]?.equity ?? 0
  const first = data[0]?.equity ?? last
  const gain = last - first
  const up = gain >= 0
  const stroke = up ? "#00ff41" : "#ff3333"

  return (
    <InteractiveCard
      title="EQUITY CURVE"
      tooltip="Balance over time; glow intensity scales with PnL magnitude"
      accent={stroke}
      expanded={
        <div className="space-y-1 mono">
          <div>Net PnL: <NumberTicker value={pnl} format={v => (v>=0?"+":"")+"$"+v.toFixed(2)} /></div>
          <div>Peak:    ${peak.toFixed(2)}</div>
          <div>Drawdown: {((1 - last/peak)*100).toFixed(2)}%</div>
        </div>
      }
    >
      <div className="h-48" style={{ filter: `drop-shadow(0 0 6px ${stroke}66)` }}>
        <ResponsiveContainer>
          <AreaChart data={data} margin={{ left: 0, right: 0, top: 6, bottom: 0 }}>
            <defs>
              <linearGradient id="eqFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%"   stopColor={stroke} stopOpacity={0.5} />
                <stop offset="100%" stopColor={stroke} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <XAxis hide dataKey="t" />
            <YAxis hide domain={["dataMin - 10", "dataMax + 10"]} />
            <ReferenceLine y={first} stroke="var(--border)" strokeDasharray="2 4" />
            <Tooltip
              contentStyle={{
                background: "var(--panel)",
                border: "1px solid var(--border)",
                borderRadius: 0, fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
              }}
              labelFormatter={() => ""}
              formatter={(v) => ["$"+v.toFixed(2), "Equity"]}
            />
            <Area
              type="monotone"
              dataKey="equity"
              stroke={stroke}
              strokeWidth={2}
              fill="url(#eqFill)"
              isAnimationActive={true}
              animationDuration={500}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </InteractiveCard>
  )
}
