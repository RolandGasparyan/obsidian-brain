import { AreaChart, Area, ResponsiveContainer, YAxis, XAxis, Tooltip, CartesianGrid } from "recharts"

export default function ConfidenceGraph({ data }) {
  return (
    <div className="h-56">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="confFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%"   stopColor="#00ff41" stopOpacity={0.55} />
              <stop offset="100%" stopColor="#00ff41" stopOpacity={0.01} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" strokeDasharray="2 4" vertical={false} />
          <XAxis hide dataKey="t" />
          <YAxis hide domain={[0, 1]} />
          <Tooltip
            contentStyle={{
              background: "var(--panel)",
              border: "1px solid var(--border)",
              borderRadius: 0, fontSize: 11,
              fontFamily: "'JetBrains Mono', monospace",
            }}
            labelFormatter={() => ""}
            formatter={(v) => [(v*100).toFixed(1)+"%", "Confidence"]}
          />
          <Area
            type="monotone"
            dataKey="confidence"
            stroke="#00ff41"
            strokeWidth={2}
            fill="url(#confFill)"
            isAnimationActive={true}
            animationDuration={600}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
