import { createContext, useContext, useEffect, useMemo, useReducer, useRef, useState } from "react"

const AppCtx = createContext(null)
export const useApp = () => useContext(AppCtx)

const PREFS_KEY = "qwr.prefs.v1"
const defaultPrefs = {
  sound:     true,
  intensity: 0.8,    // 0..1 animation intensity
  threeD:    true,
  reducedMotion: false,
}

function loadPrefs() {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (!raw) return defaultPrefs
    return { ...defaultPrefs, ...JSON.parse(raw) }
  } catch { return defaultPrefs }
}

// ── Real initial state — all zeros, populated from live API ─────────────────
const initialState = {
  balance:     0,
  peakBalance: 0,
  pnl:         0,
  regime:      0,
  confidence:  0,
  sharpe:      0,
  survival:    0,
  latency:     0,
  slippage:    0,
  spread:      0,
  riskExposure:0,
  winRate:     0,
  trades:      0,
  wins:        0,
  losses:      0,
  lastEvent:   null,
  agents:      [],
  tick:        0,
  sessionId:   "",
  live:        false,
  lastUpdated: null,
}

function reducer(s, a) {
  switch (a.type) {
    case "api_update": {
      const d = a.payload
      const agents = Array.isArray(d.agents) ? d.agents : []
      const totalCapital = agents.reduce((sum, ag) => sum + (ag.capital || 0), 0)
      const totalPnl = agents.reduce((sum, ag) => sum + (ag.total_pnl || 0), 0)
      const totalTrades = agents.reduce((sum, ag) => sum + (ag.total_trades || 0), 0)
      const totalWins = agents.reduce((sum, ag) => sum + (ag.wins || 0), 0)
      const winRate = totalTrades > 0 ? totalWins / totalTrades : 0
      const peak = Math.max(s.peakBalance, totalCapital)
      const dd = peak > 0 ? (peak - totalCapital) / peak : 0
      return {
        ...s,
        balance:     totalCapital,
        peakBalance: peak,
        pnl:         totalPnl,
        trades:      totalTrades,
        wins:        totalWins,
        losses:      totalTrades - totalWins,
        winRate:     winRate,
        regime:      Math.min(1, winRate),
        confidence:  Math.min(1, winRate * 1.2),
        survival:    Math.max(0, 1 - dd),
        sharpe:      d.sharpe || 0,
        latency:     d.latency || 0,
        riskExposure:dd,
        agents:      agents,
        tick:        d.tick || s.tick,
        sessionId:   d.session_id || s.sessionId,
        live:        true,
        lastUpdated: Date.now(),
      }
    }
    case "api_error": {
      return { ...s, live: false }
    }
    default: return s
  }
}

export function AppProvider({ children }) {
  const [prefs, setPrefs] = useState(loadPrefs)
  const [state, dispatch] = useReducer(reducer, initialState)
  const [intro, setIntro] = useState(true)

  useEffect(() => {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  }, [prefs])

  // ── Live polling from real engine API every 5 seconds ───────────────────────
  const pollRef = useRef()
  useEffect(() => {
    let dead = false
    const poll = async () => {
      try {
        const r = await fetch("/api/engine-state", { cache: "no-store" })
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const data = await r.json()
        if (!dead) dispatch({ type: "api_update", payload: data })
      } catch (e) {
        if (!dead) dispatch({ type: "api_error", error: e.message })
      }
      if (!dead) pollRef.current = setTimeout(poll, 5000)
    }
    poll()
    return () => { dead = true; clearTimeout(pollRef.current) }
  }, [])

  const setPref = (k, v) => setPrefs(p => ({ ...p, [k]: v }))

  const value = useMemo(() => ({
    state, dispatch, prefs, setPref, intro, setIntro,
  }), [state, prefs, intro])

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>
}
