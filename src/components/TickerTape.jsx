import { useEffect, useState } from "react"

const PAIRS = [
  { sym: "BTC/USDT",  px: 77612.4 },
  { sym: "ETH/USDT",  px:  2319.8 },
  { sym: "SOL/USDT",  px:    85.7 },
  { sym: "BNB/USDT",  px:   636.7 },
  { sym: "XRP/USDT",  px:     1.417 },
  { sym: "ADA/USDT",  px:     0.2475 },
  { sym: "DOGE/USDT", px:     0.0964 },
  { sym: "AVAX/USDT", px:     9.27 },
  { sym: "LINK/USDT", px:     9.26 },
]

export default function TickerTape() {
  const [rows, setRows] = useState(() =>
    PAIRS.map(p => ({ ...p, chg: (Math.random()-0.5)*0.012 }))
  )

  useEffect(() => {
    const t = setInterval(() => {
      setRows(rs => rs.map(r => {
        const d = (Math.random()-0.5)*0.0012
        const px = r.px * (1 + d)
        return { ...r, px, chg: r.chg + d }
      }))
    }, 900)
    return () => clearInterval(t)
  }, [])

  const items = [...rows, ...rows]

  return (
    <div className="relative overflow-hidden border-y border-[color:var(--border)] bg-[color:var(--panel)]">
      <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-[color:var(--bg)] to-transparent z-10" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-[color:var(--bg)] to-transparent z-10" />
      <div
        className="flex whitespace-nowrap gap-8 py-2 pk text-[8px]"
        style={{ animation: "qwr-marquee 60s linear infinite" }}
      >
        {items.map((r, i) => {
          const up = r.chg >= 0
          return (
            <span key={i} className="inline-flex items-center gap-2 tracking-widest">
              <span className="text-[color:var(--subdim)]">{r.sym}</span>
              <span className="text-[color:var(--text)]">
                {r.px < 10 ? r.px.toFixed(4) : r.px.toFixed(2)}
              </span>
              <span style={{ color: up ? "var(--green)" : "var(--red)" }}>
                {up ? "▲" : "▼"} {Math.abs(r.chg*100).toFixed(2)}%
              </span>
            </span>
          )
        })}
      </div>
    </div>
  )
}
