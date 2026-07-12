import { useEffect, useState } from "react"
import { motion } from "framer-motion"

/**
 * L99StatusPanel — public-facing widget showing the Champion-mode
 * system's live state: stage, equity, BTC vol regime, per-engine
 * activity + viability metrics. Reads /api/l99-status.json (published
 * every minute by a cron on the VPS).
 *
 * Defensive design — never crashes the page, even if the endpoint is
 * 404 or returns malformed JSON. Falls back to a "ENGINES OFFLINE"
 * card so the user knows status is just unavailable.
 */

const ENGINE_META = {
  godmode: {
    name:    "GODMODE",
    sub:     "Futures · Microstructure · 2-5min",
    color:   "#ff5577",
  },
  aegis_alpha: {
    name:    "AEGIS-ALPHA",
    sub:     "Spot · Momentum · 4-72h",
    color:   "#00ffff",
  },
  quant_predator: {
    name:    "QUANT-PREDATOR",
    sub:     "MTF · Position · 2-14d",
    color:   "#ffaa33",
  },
}

const STAGE_LABEL = {
  1: { label: "STAGE 1 · ULTRA AGGRESSIVE",      color: "#ff5577" },
  2: { label: "STAGE 2 · CONTROLLED AGGRESSION", color: "#ffaa33" },
  3: { label: "STAGE 3 · OPTIMIZED RISK",        color: "#ffff00" },
  4: { label: "STAGE 4 · CAPITAL PRESERVATION",  color: "#00ff41" },
}


export default function L99StatusPanel({ pollMs = 60_000 }) {
  const [data,    setData]    = useState(null)
  const [loaded,  setLoaded]  = useState(false)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    let dead = false
    let to
    const tick = async () => {
      try {
        const r = await fetch("/api/l99-status.json", { cache: "no-store" })
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const j = await r.json()
        if (!dead) { setData(j); setError(null); setLoaded(true) }
      } catch (e) {
        if (!dead) { setError(e.message); setLoaded(true) }
      } finally {
        to = setTimeout(tick, pollMs)
      }
    }
    tick()
    return () => { dead = true; clearTimeout(to) }
  }, [pollMs])

  if (!loaded) return null   // first-render skeleton

  if (error || !data) {
    return (
      <div className="qwr-panel p-4 md:p-5 space-y-2"
           style={{ borderColor: "rgba(255,170,51,0.3)" }}>
        <div className="pk text-[10px] tracking-widest"
             style={{ color: "#ffaa33", textShadow: "0 0 8px rgba(255,170,51,0.4)" }}>
          ◆ L99 STATUS · OFFLINE
        </div>
        <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)]">
          {error ? `error: ${error}` : "no data yet"}
        </div>
      </div>
    )
  }

  const stage = data?.engines?.aegis_alpha?.snapshot?.stage ?? 1
  const stageInfo = STAGE_LABEL[stage] || STAGE_LABEL[1]
  const startEq = data.starting_equity || 3000
  const liveEq  = data?.engines?.aegis_alpha?.snapshot?.equity ?? startEq
  const btcPct  = data?.engines?.aegis_alpha?.snapshot?.btc_vol_pctile ?? null
  const killed  = !!data.killed
  const ageS    = data.generated_at_ns
    ? Math.max(0, Math.round((Date.now() * 1e6 - data.generated_at_ns) / 1e9))
    : null
  const fresh   = ageS !== null && ageS < 180

  const btcRegime = btcPct == null ? "—"
                  : btcPct >= 0.80 ? "HIGH VOL ×0.7"
                  : btcPct <= 0.20 ? "LOW VOL ×0.8"
                  : "NORMAL ×1.0"
  const btcColor  = btcPct == null ? "#888"
                  : btcPct >= 0.80 ? "#ff5577"
                  : btcPct <= 0.20 ? "#ffaa33"
                  : "#00ff41"

  return (
    <div className="qwr-panel p-4 md:p-5 space-y-4"
         style={{ borderColor: killed ? "rgba(255,85,119,0.5)"
                                       : "rgba(0,255,65,0.35)",
                  boxShadow: killed ? "0 0 14px rgba(255,85,119,0.3)"
                                    : "0 0 14px rgba(0,255,65,0.20)" }}>
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <span className="relative inline-block">
            <span className="inline-block w-2 h-2 rounded-full"
                  style={{ background: killed ? "#ff5577"
                                              : fresh ? "#00ff41" : "#ff9933",
                           boxShadow: killed ? "0 0 8px #ff5577"
                                             : fresh ? "0 0 8px #00ff41"
                                                     : "0 0 8px #ff9933" }} />
            {fresh && !killed && (
              <motion.span className="absolute inset-0 rounded-full"
                            style={{ background: "#00ff41" }}
                            animate={{ scale: [1, 2.4, 1], opacity: [0.6, 0, 0.6] }}
                            transition={{ duration: 1.8, repeat: Infinity }} />
            )}
          </span>
          <span className="pk text-[10px] tracking-widest"
                style={{ color: killed ? "#ff5577"
                                       : fresh ? "#00ff41" : "#ff9933" }}>
            {killed ? "🛑 L99 HALTED"
                    : fresh ? "◆ L99 LIVE" : "◆ L99 STALE"}
          </span>
        </div>
        <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)]">
          {ageS !== null ? `${ageS}s ago` : "—"}
        </div>
      </div>

      {/* Top stats — stage / equity / BTC vol regime */}
      <div className="grid grid-cols-3 gap-2 md:gap-3">
        <Stat label="STAGE" value={stage} sub={stageInfo.label.split("·")[1]?.trim()}
              color={stageInfo.color} />
        <Stat label="EQUITY" value={`$${(liveEq).toFixed(0)}`}
              sub={`from $${startEq.toFixed(0)}`} color="#00ff41" />
        <Stat label="BTC VOL"
              value={btcPct == null ? "—" : `${(btcPct * 100).toFixed(0)}%`}
              sub={btcRegime} color={btcColor} />
      </div>

      {/* Per-engine grid */}
      <div className="space-y-2">
        {["godmode", "aegis_alpha", "quant_predator"].map(eid => {
          const meta  = ENGINE_META[eid]
          const block = data.engines?.[eid] || {}
          return <EngineRow key={eid} meta={meta} block={block} />
        })}
      </div>

      {/* Footer mini-link */}
      <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)]
                       text-right">
        json: <a href="/api/l99-status.json" target="_blank"
                  rel="noreferrer" className="underline">/api/l99-status.json</a>
      </div>
    </div>
  )
}


function Stat({ label, value, sub, color = "#00ff41" }) {
  return (
    <div className="qwr-panel p-3">
      <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mb-1">
        {label}
      </div>
      <div className="pk text-base md:text-lg"
           style={{ color, textShadow: `0 0 6px ${color}66` }}>
        {value}
      </div>
      {sub && (
        <div className="pk text-[6px] tracking-widest text-[color:var(--subdim)] mt-1">
          {sub}
        </div>
      )}
    </div>
  )
}


function EngineRow({ meta, block }) {
  const enabled = !!block.enabled
  const snap    = block.snapshot
  const viab    = block.viability
  const ageS    = block.snapshot_age_s ?? null
  const dotColor = !enabled ? "#666"
                  : (snap && ageS !== null && ageS < 600) ? "#00ff41"
                  : "#ff9933"

  return (
    <motion.div whileHover={{ x: 2 }}
      className="grid grid-cols-12 gap-2 items-center px-3 py-2 border"
      style={{ borderColor: meta.color + "44", background: meta.color + "08" }}>

      {/* status dot */}
      <div className="col-span-1 flex items-center justify-center">
        <span className="inline-block w-2 h-2 rounded-full"
              style={{ background: dotColor,
                       boxShadow: `0 0 6px ${dotColor}` }} />
      </div>

      {/* engine name + sub */}
      <div className="col-span-4 min-w-0">
        <div className="pk text-[10px] tracking-widest truncate"
             style={{ color: meta.color, textShadow: `0 0 4px ${meta.color}55` }}>
          {meta.name}
        </div>
        <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] truncate">
          {meta.sub}
        </div>
      </div>

      {/* trades */}
      <div className="col-span-3 pk text-[8px] tracking-widest text-[color:var(--dim)] text-center">
        {snap ?
          <>open: <span className="text-white">{snap.open_trades ?? 0}</span> ·
            closed: <span className="text-white">{snap.closed_trades ?? 0}</span>
          </>
          : <span className="text-[color:var(--subdim)]">no snapshot</span>}
      </div>

      {/* viability */}
      <div className="col-span-4 pk text-[8px] tracking-widest text-right">
        {viab && viab.n_trades > 0 ?
          <ViabilityBadge v={viab} />
          : <span className="text-[color:var(--subdim)]">
              §VI: 0/50 trades
            </span>}
      </div>
    </motion.div>
  )
}


function ViabilityBadge({ v }) {
  const ok    = !!v.is_viable
  const color = ok ? "#00ff41" : "#ff9933"
  const wr    = (v.win_rate || 0) * 100
  return (
    <span className="pk" style={{ color, textShadow: `0 0 4px ${color}55` }}>
      §VI: {v.n_trades}/50 · WR {wr.toFixed(0)}% · EV {v.ev_per_trade?.toFixed(2) ?? "—"}R
      {ok ? " ✓" : ""}
    </span>
  )
}
