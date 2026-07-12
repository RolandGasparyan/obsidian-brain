import { motion } from "framer-motion"
import { useBotStatus, derive, pairColor } from "../state/useBotStatus.js"

/**
 * Real-time live-bot summary panel. Polls /api/bots.json every 15s and
 * renders the current state of every running bot on the VPS.
 *
 * Used on:
 *   • /dashboard (ACCOUNT) — top-of-page "LIVE TRADING BOTS" block
 *   • /championship       — leaderboard feed
 *   • /arena              — to hydrate race lanes with real equity
 *
 * Design: same dark-glass qwr-panel look as the rest of the app, but
 * with a pulsing green "LIVE" dot when the data is fresh (= endpoint
 * reachable and less than ~2 minutes old).
 */
export default function LiveBotsPanel({ compact = false }) {
  const { data, live } = useBotStatus(15_000)
  const bots = data?.bots ?? []
  const agg  = derive(bots) ?? {
    totalEquity: 0, totalStart: 0, netPnl: 0, totalRoi: 0,
    totalTrades: 0, activeBots: 0, longBots: 0, botCount: 0,
  }

  const age = data?.generated_at
    ? Math.max(0, Math.round((Date.now() - new Date(data.generated_at).getTime()) / 1000))
    : null
  // Treat data as fresh if we have a recent timestamp, even if the
  // most recent poll transiently failed — avoids flicker between
  // LIVE/OFFLINE when a request hiccups.
  const hasRealData = age !== null
  const fresh = hasRealData && age < 180

  return (
    <div className="qwr-panel p-4 md:p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <span className="relative inline-block">
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{
                background: fresh ? "#00ff41" : "#ff9933",
                boxShadow: fresh ? "0 0 8px #00ff41" : "0 0 8px #ff9933",
              }}
            />
            {fresh && (
              <motion.span
                className="absolute inset-0 rounded-full"
                style={{ background: "#00ff41" }}
                animate={{ scale: [1, 2.4, 1], opacity: [0.6, 0, 0.6] }}
                transition={{ duration: 1.8, repeat: Infinity }}
              />
            )}
          </span>
          <span
            className="pk text-[10px] tracking-widest"
            style={{ color: fresh ? "#00ff41" : "#ff9933" }}
          >
            {fresh ? "◆ LIVE BOTS" : hasRealData ? "◆ STALE" : "◆ OFFLINE — DEMO"}
          </span>
        </div>
        <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)]">
          {data?.generated_at
            ? `${age ?? "?"}s ago · ${agg.activeBots}/${agg.botCount} active`
            : "mock data"}
        </div>
      </div>

      {/* Aggregate row */}
      {!compact && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3">
          <Kv label="EQUITY" value={`$${agg.totalEquity.toFixed(2)}`} color="#00ff41" />
          <Kv
            label="NET PnL"
            value={`${agg.netPnl >= 0 ? "+" : ""}$${agg.netPnl.toFixed(2)}`}
            color={agg.netPnl >= 0 ? "#00ff41" : "#ff5577"}
          />
          <Kv
            label="ROI"
            value={`${agg.totalRoi >= 0 ? "+" : ""}${agg.totalRoi.toFixed(2)}%`}
            color={agg.totalRoi >= 0 ? "#00ff41" : "#ff5577"}
          />
          <Kv label="TRADES" value={agg.totalTrades} color="#ffff00" />
        </div>
      )}

      {/* Per-bot rows */}
      <div className="space-y-2">
        {bots.map(b => <BotRow key={b.pair} b={b} />)}
        {bots.length === 0 && (
          <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] text-center py-4">
            Waiting for first refresh…
          </div>
        )}
      </div>
    </div>
  )
}

function Kv({ label, value, color = "#00ff41" }) {
  return (
    <div className="qwr-panel p-3">
      <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mb-1">{label}</div>
      <div
        className="pk text-sm md:text-base"
        style={{ color, textShadow: `0 0 6px ${color}66` }}
      >
        {value}
      </div>
    </div>
  )
}

function BotRow({ b }) {
  const color = pairColor(b.pair)
  const longPos = b.pos === "LONG"
  const roi     = Number(b.roi_pct) || 0
  const equity  = Number(b.equity)  || 0
  const active  = b.state === "active"
  const posColor = longPos ? "#00ff41" : "#808080"

  return (
    <motion.div
      whileHover={{ x: 2 }}
      className="grid grid-cols-12 gap-2 items-center px-3 py-2 border"
      style={{ borderColor: color + "44", background: color + "08" }}
    >
      {/* symbol + status */}
      <div className="col-span-3 md:col-span-2 flex items-center gap-2 min-w-0">
        <span
          className="inline-block w-2 h-2 rounded-full flex-shrink-0"
          style={{
            background: active ? "#00ff41" : "#ff5577",
            boxShadow: `0 0 6px ${active ? "#00ff41" : "#ff5577"}`,
          }}
        />
        <span
          className="pk text-[9px] md:text-[10px] tracking-widest truncate"
          style={{ color, textShadow: `0 0 4px ${color}66` }}
        >
          {b.pair.replace("_USDT", "")}
        </span>
      </div>

      {/* position */}
      <div className="col-span-2 pk text-[8px] md:text-[9px] tracking-widest"
           style={{ color: posColor }}>
        {longPos ? "◆ LONG" : "○ USDT"}
      </div>

      {/* price */}
      <div className="col-span-3 md:col-span-2 pk text-[8px] md:text-[9px] tracking-widest text-[color:var(--dim)] text-right tabular-nums">
        ${fmtPrice(b.price)}
      </div>

      {/* equity */}
      <div className="col-span-2 md:col-span-3 pk text-[9px] md:text-[10px] tracking-widest text-right tabular-nums"
           style={{ color: equity >= 250 ? "#00ff41" : "#ff5577" }}>
        ${equity.toFixed(2)}
      </div>

      {/* ROI */}
      <div className="col-span-2 md:col-span-2 pk text-[9px] md:text-[10px] tracking-widest text-right tabular-nums"
           style={{ color: roi >= 0 ? "#00ff41" : "#ff5577",
                    textShadow: `0 0 6px ${(roi >= 0 ? "#00ff41" : "#ff5577")}44` }}>
        {roi >= 0 ? "+" : ""}{roi.toFixed(2)}%
      </div>

      {/* trades — only on md+ */}
      <div className="hidden md:block md:col-span-1 pk text-[8px] tracking-widest text-[color:var(--subdim)] text-right">
        {b.trades}T
      </div>
    </motion.div>
  )
}

function fmtPrice(p) {
  const n = Number(p) || 0
  if (n >= 1000) return n.toFixed(0)
  if (n >= 10)   return n.toFixed(2)
  if (n >= 0.1)  return n.toFixed(3)
  return n.toFixed(5)
}
