import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"

/**
 * TradingTerminal — L99 :: TRADING TERMINAL view at /dashboard
 *
 * v2 — Visual refactor: matches site-wide design tokens (var(--bg/--panel/--border/etc)),
 * uses .pk pixel font + .qwr-panel borders. OHLCV now read from same-origin
 * /api/battle/terminal.json (publisher fetches Gate.io server-side, no CORS).
 *
 * Per migration decisions:
 *   D1=A bridge — keep cyber pixel aesthetic, wire all data to real backend
 *   D2  — 8 strategy agents shown as bot rows
 *   D3  — pragmatic: visual FX OK, NO Math.random, NO mock fallbacks
 *   D5  — read-only: SIM TRADE disabled, AUTO toggle is display-only
 */

// ── Real-data hook (single endpoint provides everything) ──────
function useTerminal(pollMs = 5000) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [live, setLive] = useState(false)

  useEffect(() => {
    let dead = false
    let to
    const tick = async () => {
      try {
        const r = await fetch("/api/battle/terminal.json", { cache: "no-store" })
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const j = await r.json()
        if (!dead) {
          setData(j); setLive(true); setError(null)
        }
      } catch (e) {
        if (!dead) { setLive(false); setError(e.message) }
      }
      to = setTimeout(tick, pollMs)
    }
    tick()
    return () => { dead = true; clearTimeout(to) }
  }, [pollMs])

  return { data, live, error }
}

// ── RSI(14) ────────────────────────────────────────────────────
function calcRSI(closes, period = 14) {
  if (closes.length < period + 1) return []
  const out = new Array(closes.length).fill(null)
  let gain = 0, loss = 0
  for (let i = 1; i <= period; i++) {
    const ch = closes[i] - closes[i - 1]
    if (ch >= 0) gain += ch; else loss -= ch
  }
  let avgG = gain / period, avgL = loss / period
  out[period] = avgL === 0 ? 100 : 100 - (100 / (1 + avgG / avgL))
  for (let i = period + 1; i < closes.length; i++) {
    const ch = closes[i] - closes[i - 1]
    const g = ch >= 0 ? ch : 0
    const l = ch < 0 ? -ch : 0
    avgG = (avgG * (period - 1) + g) / period
    avgL = (avgL * (period - 1) + l) / period
    out[i] = avgL === 0 ? 100 : 100 - (100 / (1 + avgG / avgL))
  }
  return out
}

// ── Live clock ────────────────────────────────────────────────
function useLiveClock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  const mm = String(now.getMinutes()).padStart(2, "0")
  const ss = String(now.getSeconds()).padStart(2, "0")
  const ampm = now.getHours() >= 12 ? "PM" : "AM"
  const h12 = ((now.getHours() % 12) || 12)
  return `${String(h12).padStart(2, "0")}:${mm}:${ss} ${ampm}`
}

// ── Pixel-art candlestick (uses CSS vars) ─────────────────────
function CandleChart({ candles, width = 880, height = 380 }) {
  if (!candles || candles.length < 2) {
    return (
      <div style={{
        width, height, display: "grid", placeItems: "center",
        color: "var(--orange)", fontSize: 11,
        border: "1px dashed var(--border)",
      }} className="pk">
        — awaiting OHLCV from Gate.io —
      </div>
    )
  }
  const padL = 70, padR = 90, padT = 20, padB = 50
  const innerW = width - padL - padR
  const innerH = height - padT - padB
  const minP = Math.min(...candles.map(c => c.l))
  const maxP = Math.max(...candles.map(c => c.h))
  const range = (maxP - minP) || 1
  const cw = innerW / candles.length
  const x = (i) => padL + i * cw + cw / 2
  const y = (p) => padT + (1 - (p - minP) / range) * innerH

  const labels = [maxP, minP + range * 0.66, minP + range * 0.33, minP]
  const lastClose = candles[candles.length - 1].c
  const firstOpen = candles[0].o
  const change = lastClose - firstOpen
  const upTrend = change >= 0
  const ts = (t) => {
    const d = new Date(t)
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`
  }

  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      {/* Grid lines */}
      {labels.map((p, i) => (
        <g key={i}>
          <line x1={padL} x2={width - padR} y1={y(p)} y2={y(p)}
                stroke="var(--border)" strokeDasharray="2,4" />
          <text x={padL - 8} y={y(p) + 4} textAnchor="end"
                fontSize="10" fontFamily="monospace" fill="var(--orange)">
            {p.toFixed(1)}
          </text>
        </g>
      ))}
      {/* Current price line */}
      <line x1={padL} x2={width - padR} y1={y(lastClose)} y2={y(lastClose)}
            stroke="var(--green)" strokeDasharray="3,3" strokeOpacity="0.6" />
      {/* Candles */}
      {candles.map((c, i) => {
        const up = c.c >= c.o
        const color = up ? "var(--green)" : "var(--pink)"
        const yo = y(c.o), yc = y(c.c), yh = y(c.h), yl = y(c.l)
        const bodyTop = Math.min(yo, yc)
        const bodyH = Math.max(1, Math.abs(yc - yo))
        const bw = Math.max(2, cw - 4)
        return (
          <g key={i}>
            <line x1={x(i)} x2={x(i)} y1={yh} y2={yl} stroke={color} strokeWidth="1" />
            <rect x={x(i) - bw / 2} y={bodyTop} width={bw} height={bodyH} fill={color} />
          </g>
        )
      })}
      {/* Price flag right side */}
      <rect x={width - padR + 4} y={y(lastClose) - 10}
            width={padR - 8} height={20} fill="var(--green)" />
      <text x={width - padR / 2 + 2} y={y(lastClose) + 4} textAnchor="middle"
            fontSize="11" fontFamily="monospace" fill="#000" fontWeight="bold">
        {lastClose.toFixed(1)}
      </text>
      {/* Time axis */}
      {candles.filter((_, i) => i % 5 === 0 || i === candles.length - 1).map((c) => {
        const i = candles.indexOf(c)
        return (
          <text key={i} x={x(i)} y={height - padB + 16} textAnchor="middle"
                fontSize="9" fontFamily="monospace" fill="var(--subdim)">
            {ts(c.t)}
          </text>
        )
      })}
      {/* Session-change tag (top-right) */}
      <text x={width - padR - 6} y={padT + 12} textAnchor="end"
            fontSize="13" fontFamily="monospace"
            fill={upTrend ? "var(--subdim)" : "var(--pink)"}>
        {upTrend ? "+" : "-"}${Math.abs(change).toFixed(2)}
      </text>
    </svg>
  )
}

// ── RSI strip ────────────────────────────────────────────────
function RsiStrip({ candles, width = 880, height = 60 }) {
  const rsi = useMemo(() => calcRSI(candles.map(c => c.c), 14), [candles])
  if (rsi.filter(v => v !== null).length < 2) {
    return (
      <div style={{ height, color: "var(--subdim)", fontSize: 10, padding: "10px 70px" }} className="pk">
        RSI · MOMENTUM · 14P · awaiting data
      </div>
    )
  }
  const padL = 70, padR = 90, padT = 12, padB = 12
  const innerW = width - padL - padR
  const innerH = height - padT - padB
  const cw = innerW / rsi.length
  const x = (i) => padL + i * cw + cw / 2
  const y = (v) => padT + (1 - v / 100) * innerH
  const last = rsi[rsi.length - 1]

  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <line x1={padL} x2={width - padR} y1={y(30)} y2={y(30)}
            stroke="var(--pink)" strokeDasharray="2,4" opacity="0.5" />
      <line x1={padL} x2={width - padR} y1={y(50)} y2={y(50)} stroke="var(--border)" />
      <line x1={padL} x2={width - padR} y1={y(70)} y2={y(70)}
            stroke="var(--orange)" strokeDasharray="2,4" opacity="0.5" />
      <text x={padL - 8} y={y(70) + 3} textAnchor="end" fontSize="9"
            fontFamily="monospace" fill="var(--orange)">70</text>
      <text x={padL - 8} y={y(50) + 3} textAnchor="end" fontSize="9"
            fontFamily="monospace" fill="var(--subdim)">50</text>
      <text x={padL - 8} y={y(30) + 3} textAnchor="end" fontSize="9"
            fontFamily="monospace" fill="var(--pink)">30</text>
      <text x={padL - 35} y={padT + 8} fontSize="9" fontFamily="monospace"
            fill="var(--teal)" className="pk">RSI · MOMENTUM · 14P</text>
      {rsi.map((v, i) => {
        if (v === null || i === 0) return null
        const prev = rsi[i - 1]
        if (prev === null) return null
        const color = v >= 70 ? "var(--orange)" : v <= 30 ? "var(--pink)" : "var(--green)"
        return <line key={i} x1={x(i - 1)} y1={y(prev)} x2={x(i)} y2={y(v)}
                     stroke={color} strokeWidth="2" />
      })}
      {last !== null && Number.isFinite(last) && (
        <text x={width - padR + 8} y={y(last) + 4} fontSize="11"
              fontFamily="monospace" fill="var(--text)" fontWeight="bold">
          {last.toFixed(1)}
        </text>
      )}
    </svg>
  )
}

// ── Status pill (matches site nav-pill aesthetic) ────────────
function StatusPill({ label, ok, accent = "var(--green)" }) {
  const c = ok ? accent : "var(--red)"
  return (
    <div className="pk" style={{
      border: `1px solid ${c}`, padding: "5px 10px",
      display: "inline-flex", alignItems: "center", gap: 8,
      fontSize: 9, color: c, background: "rgba(0,0,0,0.45)",
    }}>
      <span style={{
        display: "inline-block", width: 6, height: 6, borderRadius: 999,
        background: c, boxShadow: `0 0 6px ${c}`,
      }}/>
      {label}
    </div>
  )
}

// ── KV row (used by Portfolio + Kill Switch tables) ──────────
function KVRow({ label, children, dim = false }) {
  return (
    <tr style={{ borderBottom: "1px dashed var(--border)" }}>
      <td className="pk" style={{
        padding: "9px 0", color: "var(--subdim)", fontSize: 9,
      }}>{label}</td>
      <td style={{
        padding: "9px 0", textAlign: "right", color: "var(--text)",
        fontFamily: "monospace", fontSize: 12,
      }}>{children}</td>
    </tr>
  )
}

// ── Section header (matches LandingPage / RacingArena pattern) ─
function SectionHeader({ title, right, accent = "var(--orange)" }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      paddingBottom: 8, marginBottom: 12,
      borderBottom: "1px dashed var(--border)",
    }}>
      <div className="pk" style={{ fontSize: 10, color: accent, letterSpacing: 2 }}>
        {title}
      </div>
      {right}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────
export default function TradingTerminal() {
  const { data: terminal, live } = useTerminal(5000)
  const [pair, setPair] = useState("BTC/USDT")
  const clock = useLiveClock()

  const candles = (terminal?.ohlcv?.[pair]) || []
  const tickers = terminal?.pair_tickers || {}
  const tBtc = terminal?.ticker
  const tSel = tickers[pair] || {}

  const ohlc24h = {
    o: candles.length ? candles[0].o : 0,
    h: tSel.high_24h || (candles.length ? Math.max(...candles.map(c => c.h)) : 0),
    l: tSel.low_24h || (candles.length ? Math.min(...candles.map(c => c.l)) : 0),
    v: tSel.volume || (candles.length ? candles.reduce((s, c) => s + c.v, 0) : 0),
  }

  const pairs = terminal?.pairs || ["BTC/USDT"]
  const port  = terminal?.portfolio || {}
  const ks    = terminal?.killswitch || {}
  const bot   = terminal?.bot || {}
  const ses   = terminal?.session || {}

  return (
    <div style={{
      padding: "20px 28px", minHeight: "100vh",
      color: "var(--text)", position: "relative",
      // The Shell parent renders SpaceBackground at z-index 0,
      // we sit above it with explicit z-index + opaque-ish backdrop
      zIndex: 1,
    }}>
      {/* ── Header ─────────────────────────────────────── */}
      <div style={{
        display: "flex", justifyContent: "space-between",
        alignItems: "flex-start", marginBottom: 24,
        gap: 24, flexWrap: "wrap",
      }}>
        <div>
          <div className="pk" style={{
            fontSize: 22, color: "var(--orange)", letterSpacing: 2,
            textShadow: "0 0 10px rgba(255,136,0,0.4)",
          }}>
            L99 :: TRADING
          </div>
          <div className="pk" style={{
            fontSize: 22, color: "var(--orange)", letterSpacing: 2,
            textShadow: "0 0 10px rgba(255,136,0,0.4)",
          }}>
            TERMINAL
          </div>
          <div className="pk" style={{
            fontSize: 8, color: "var(--pink)", marginTop: 8, letterSpacing: 1,
          }}>
            arena · enterprise_runtime · 8-agent battle
          </div>
        </div>

        <div style={{
          display: "flex", alignItems: "center", gap: 8, fontSize: 11,
          fontFamily: "monospace", color: "var(--green)",
          padding: "12px 0",
        }}>
          <span>BTC/USDT</span>
          <span style={{ color: "var(--subdim)" }}> · 1m · </span>
          <span style={{ fontWeight: "bold" }}>
            {tBtc?.price ? tBtc.price.toFixed(1) : "—"}
          </span>
          <span style={{ color: tBtc?.change_pct_24h >= 0 ? "var(--green)" : "var(--red)" }}>
            {tBtc?.change_pct_24h != null
              ? `${tBtc.change_pct_24h >= 0 ? "+" : ""}${tBtc.change_pct_24h.toFixed(2)}%`
              : "—"}
          </span>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <StatusPill label={`L99BOT · ${bot.alive ? "UP" : "DOWN"}`}
                       ok={!!bot.alive} accent="var(--green)" />
          <StatusPill label={`SESSION ${ses.open ? "OPEN" : "CLOSED"}`}
                       ok={!!ses.open} accent="var(--orange)" />
          <StatusPill label={clock} ok={true} accent="var(--teal)" />
        </div>
      </div>

      {/* ── Main grid: chart + balance ─────────────────── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 2fr) minmax(280px, 1fr)",
        gap: 20, marginBottom: 20,
      }}>
        {/* LIVE TAPE */}
        <div className="qwr-panel" style={{ padding: 16, background: "var(--panel)" }}>
          <SectionHeader
            title="LIVE TAPE"
            right={
              <div style={{ display: "flex", alignItems: "center", gap: 18,
                            fontSize: 9, fontFamily: "monospace" }}>
                <span className="pk" style={{ color: "var(--pink)" }}>+ UFO ACTIVE +</span>
                <span style={{ color: "var(--subdim)" }}>
                  VPS · 167.71.24.86 · GATE.IO SPOT
                </span>
              </div>
            }
          />

          <CandleChart candles={candles} width={880} height={380} />
          <RsiStrip candles={candles} width={880} height={60} />

          {/* Pair selector */}
          <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
            <button disabled className="pk" style={{
              border: "1px solid var(--dim)", padding: "6px 12px",
              color: "var(--dim)", background: "transparent",
              fontSize: 9, cursor: "not-allowed", letterSpacing: 1,
            }}>
              + SIM TRADE
            </button>
            <button className="pk" style={{
              border: "1px solid var(--orange)", padding: "6px 12px",
              color: "var(--orange)", background: "rgba(255,136,0,0.1)",
              fontSize: 9, cursor: "default", letterSpacing: 1,
            }}>
              ◆ AUTO
            </button>
            {pairs.map(p => (
              <button key={p} onClick={() => setPair(p)} className="pk"
                style={{
                  border: `1px solid ${p === pair ? "var(--orange)" : "var(--border)"}`,
                  padding: "6px 12px",
                  color: p === pair ? "var(--orange)" : "var(--subdim)",
                  background: p === pair ? "rgba(255,136,0,0.1)" : "transparent",
                  fontSize: 9, cursor: "pointer", letterSpacing: 1,
                }}>
                {p}
              </button>
            ))}
          </div>

          {/* OHLC stats row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
                        gap: 16, marginTop: 18, paddingTop: 14,
                        borderTop: "1px dashed var(--border)" }}>
            {[
              ["OPEN", ohlc24h.o, "var(--green)"],
              ["HIGH", ohlc24h.h, "var(--green)"],
              ["LOW",  ohlc24h.l, "var(--green)"],
              ["VOL",  ohlc24h.v, "var(--orange)"],
            ].map(([label, val, color]) => (
              <div key={label}>
                <div className="pk" style={{ fontSize: 10, color: "var(--orange)",
                                              letterSpacing: 2 }}>{label}</div>
                <div style={{ fontSize: 16, color, fontFamily: "monospace",
                              marginTop: 4 }}>
                  {Number(val).toFixed(label === "VOL" ? 2 : 1)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right column: BALANCE / PORTFOLIO / KILL SWITCH */}
        <div className="qwr-panel" style={{ padding: 16, background: "var(--panel)" }}>
          <SectionHeader
            title="BALANCE"
            right={<span className="pk" style={{ fontSize: 9, color: "var(--subdim)",
                                                  letterSpacing: 2 }}>
              {bot.alive ? "LIVE" : "OFFLINE"} · USDT
            </span>}
          />
          <div style={{ fontSize: 30, color: "var(--green)",
                        fontFamily: "monospace", marginBottom: 22 }}>
            {live ? `$${(port.mark || 0).toFixed(2)}` : "ERR"}
          </div>

          <div className="pk" style={{ fontSize: 10, color: "var(--orange)",
                                        letterSpacing: 2, marginBottom: 8 }}>
            PORTFOLIO
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              <KVRow label="CASH"><span style={{ color: "var(--teal)" }}>${(port.cash || 0).toFixed(2)}</span></KVRow>
              <KVRow label="PEAK"><span style={{ color: "var(--teal)" }}>${(port.peak || 0).toFixed(2)}</span></KVRow>
              <KVRow label="MARK"><span style={{ color: "var(--teal)" }}>${(port.mark || 0).toFixed(2)}</span></KVRow>
              <KVRow label="REALIZED">
                <span style={{ color: (port.realized || 0) >= 0 ? "var(--green)" : "var(--red)" }}>
                  {(port.realized || 0) >= 0 ? "+" : ""}${Number(port.realized || 0).toFixed(4)}
                </span>
              </KVRow>
              <KVRow label="UNREAL.">
                <span style={{ color: (port.unrealized || 0) >= 0 ? "var(--green)" : "var(--red)" }}>
                  {(port.unrealized || 0) >= 0 ? "+" : ""}${Number(port.unrealized || 0).toFixed(4)}
                </span>
              </KVRow>
              <KVRow label="B / S">
                <span style={{ color: "var(--orange)" }}>{port.buys ?? 0} / {port.sells ?? 0}</span>
              </KVRow>
            </tbody>
          </table>

          <div className="pk" style={{ fontSize: 10, color: "var(--orange)",
                                        letterSpacing: 2, marginTop: 22, marginBottom: 8 }}>
            KILL SWITCH
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              <KVRow label="HALTED">
                <span style={{ color: ks.halted ? "var(--red)" : "var(--green)" }}>
                  {ks.halted ? "YES" : "NO"}
                </span>
              </KVRow>
              <KVRow label="CONSEC L">
                <span style={{ color: "var(--green)" }}>
                  {ks.consec_loss ?? 0} / {ks.consec_loss_max ?? 5}
                </span>
              </KVRow>
              <KVRow label="MTM DD">
                <span style={{ color: "var(--green)" }}>
                  {(ks.mtm_dd_pct ?? 0).toFixed(2)}% / {(ks.mtm_dd_max_pct ?? 21).toFixed(0)}%
                </span>
              </KVRow>
              <KVRow label="REGIME">
                <span style={{ color: "var(--teal)", fontSize: 10 }}>
                  {bot.regime || "—"} · {bot.mode || "—"}
                </span>
              </KVRow>
              <KVRow label="CYCLE">
                <span style={{ color: "var(--teal)" }}>{bot.cycle ?? 0}</span>
              </KVRow>
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Agents leaderboard ─────────────────────────── */}
      <div className="qwr-panel" style={{ padding: 16, marginBottom: 20,
                                            background: "var(--panel)" }}>
        <SectionHeader title="AGENTS · 8-AGENT BATTLE"
                        right={<span className="pk" style={{ fontSize: 9,
                                                              color: "var(--subdim)",
                                                              letterSpacing: 2 }}>
          L99 STANDARDIZATION · ARTICLE V
        </span>} />
        <table style={{ width: "100%", borderCollapse: "collapse",
                        fontFamily: "monospace", fontSize: 11 }}>
          <thead>
            <tr className="pk" style={{ color: "var(--orange)", fontSize: 9, letterSpacing: 1 }}>
              <th style={{ textAlign: "left", padding: "8px 0" }}>AGENT</th>
              <th style={{ textAlign: "right" }}>$BUCKET</th>
              <th style={{ textAlign: "right" }}>PNL</th>
              <th style={{ textAlign: "right" }}>TR</th>
              <th style={{ textAlign: "right" }}>WR%</th>
              <th style={{ textAlign: "right" }}>SHARPE</th>
              <th style={{ textAlign: "right" }}>vDD%</th>
              <th style={{ textAlign: "right" }}>STATE</th>
            </tr>
          </thead>
          <tbody>
            {(terminal?.agents || []).map(a => (
              <tr key={a.id} style={{ borderTop: "1px dashed var(--border)",
                                       opacity: a.disabled ? 0.4 : 1 }}>
                <td style={{ padding: "8px 0", color: "var(--teal)" }}>
                  {String(a.id).padStart(2, "0")} · {a.label}
                </td>
                <td style={{ textAlign: "right", color: "var(--green)" }}>
                  ${a.vbucket.toFixed(2)}
                </td>
                <td style={{ textAlign: "right",
                             color: a.pnl > 0 ? "var(--green)" : a.pnl < 0 ? "var(--red)" : "var(--subdim)" }}>
                  {a.pnl > 0 ? "+" : ""}{a.pnl.toFixed(2)}
                </td>
                <td style={{ textAlign: "right", color: "var(--subdim)" }}>{a.trades}</td>
                <td style={{ textAlign: "right", color: "var(--subdim)" }}>
                  {a.win_rate.toFixed(0)}
                </td>
                <td style={{ textAlign: "right", color: "var(--subdim)" }}>
                  {a.sharpe.toFixed(2)}
                </td>
                <td style={{ textAlign: "right", color: "var(--subdim)" }}>
                  {a.vDD_pct.toFixed(2)}
                </td>
                <td style={{ textAlign: "right",
                             color: a.disabled ? "var(--red)" : "var(--green)" }}>
                  {a.disabled ? "DISABLED" : "ARMED"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Stream footer ──────────────────────────────── */}
      <div className="pk" style={{
        fontSize: 8, color: "var(--subdim)", letterSpacing: 1,
        display: "flex", justifyContent: "space-between",
        paddingTop: 8, borderTop: "1px dashed var(--border)",
      }}>
        <div>
          stream {live ? "● live" : "○ offline"} ·
          ts: {terminal?.ts || "—"} ·
          uptime: {Math.floor((bot.uptime_sec || 0) / 60)}m
        </div>
        <div>
          publisher: /api/battle/terminal.json · cron 1min
        </div>
      </div>
    </div>
  )
}
