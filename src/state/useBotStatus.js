import { useEffect, useState } from "react"

/**
 * Polls /api/bots.json (populated every minute by a cron on the VPS).
 *
 * In dev (vite serves port 5173), no /api path is populated, so we show
 * mock data with a `live: false` flag. In production the same hook
 * returns live data from the same origin.
 *
 * Shape returned by the JSON endpoint:
 *   { generated_at: ISO, bots: [
 *       { pair, state, restarts, mem_bytes, pos, price,
 *         equity, roi_pct, trades }, …
 *     ] }
 */

// Balance each paper bot started with (keep in sync with the systemd
// unit's `--balance` arg).
const START_BALANCE_PER_BOT = 250
const TOTAL_START_BALANCE   = START_BALANCE_PER_BOT * 4

// Mock fallback so dev works without the VPS
const MOCK = {
  generated_at: null,
  bots: [
    { pair: "ETH_USDT",  state: "mock", restarts: 0, pos: "LONG", price: 2320, equity: 250, roi_pct: 0, trades: 0 },
    { pair: "SOL_USDT",  state: "mock", restarts: 0, pos: "USDT", price: 86,   equity: 250, roi_pct: 0, trades: 0 },
    { pair: "XRP_USDT",  state: "mock", restarts: 0, pos: "LONG", price: 1.44, equity: 250, roi_pct: 0, trades: 0 },
    { pair: "AVAX_USDT", state: "mock", restarts: 0, pos: "USDT", price: 9.4,  equity: 250, roi_pct: 0, trades: 0 },
  ],
}

const PAIR_COLOR = {
  ETH_USDT:  "#627eea",
  SOL_USDT:  "#14f195",
  XRP_USDT:  "#23292f",
  AVAX_USDT: "#e84142",
  BTC_USDT:  "#f7931a",
  BNB_USDT:  "#f3ba2f",
  DOGE_USDT: "#c3a634",
}

export const AGENT_COLORS = {
  ETH:  "#627eea",
  SOL:  "#14f195",
  XRP:  "#00ffff",
  AVAX: "#ff5577",
  BTC:  "#ffa500",
}

// 1-million USDT prize pool — matches the championship page rules
export const FINISH_LINE = 1_000_000

export function pairColor(pair) {
  return PAIR_COLOR[pair] || "#00ffff"
}

/**
 * Derive a few common aggregates so every consumer computes them the
 * same way.
 */
export function derive(bots) {
  if (!Array.isArray(bots) || bots.length === 0) return null
  const totalEquity = bots.reduce((s, b) => s + (Number(b.equity) || 0), 0)
  const totalStart  = START_BALANCE_PER_BOT * bots.length
  const netPnl      = totalEquity - totalStart
  const totalRoi    = (netPnl / totalStart) * 100
  const totalTrades = bots.reduce((s, b) => s + (Number(b.trades) || 0), 0)
  const activeBots  = bots.filter(b => b.state === "active").length
  const longBots    = bots.filter(b => b.pos === "LONG").length
  return {
    totalEquity, totalStart, netPnl, totalRoi, totalTrades,
    activeBots, longBots, botCount: bots.length,
  }
}

/**
 * Low-level hook — returns { data, live, error, loading }.
 * data is always a valid shape (mock when live=false).
 */
export function useBotStatus(pollMs = 15000) {
  const [data, setData]     = useState(MOCK)
  const [live, setLive]     = useState(false)
  const [error, setError]   = useState(null)
  const [loading, setLoad]  = useState(true)

  useEffect(() => {
    let dead = false
    let to
    const tick = async () => {
      try {
        const r = await fetch("/api/bots.json", { cache: "no-store" })
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const j = await r.json()
        if (dead) return
        if (!Array.isArray(j.bots)) throw new Error("bad shape")
        setData(j)
        setLive(true)
        setError(null)
      } catch (e) {
        if (!dead) {
          setLive(false)
          setError(e.message)
        }
      } finally {
        if (!dead) setLoad(false)
      }
      to = setTimeout(tick, pollMs)
    }
    tick()
    return () => { dead = true; clearTimeout(to) }
  }, [pollMs])

  return { data, live, error, loading }
}

export { START_BALANCE_PER_BOT, TOTAL_START_BALANCE }
