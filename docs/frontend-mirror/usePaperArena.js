/**
 * usePaperArena — React hook for the 8-agent paper-battle arena.
 *
 * Reads /api/battle/paper-arena.json published every 5s by
 * /root/agent/paper_battle/paper_battle_engine.py (paper-arena.service).
 *
 * ⚠️  PAPER / SIMULATION ONLY:
 *   - All pnl, trades, outcomes are SIMULATED.
 *   - No real capital is at risk.
 *   - No exchange orders are sent.
 *   - Layer 1 trading core remains LOCKED.
 *
 * Returns:
 *   {
 *     data: { mode, disclaimer, agents[], rivalries[], events[], commentary[], market, ... } | null,
 *     loading: boolean,
 *     error: string | null,
 *     isPaperMode: boolean,
 *     lastUpdated: Date | null
 *   }
 *
 * Polls every 5s to match engine cadence.
 *
 * Added 2026-05-13 per operator SAFE EVOLUTION MODE spec.
 */
import { useEffect, useState } from "react"

const PAPER_ARENA_URL = "/api/battle/paper-arena.json"
const POLL_INTERVAL_MS = 5000  // match engine tick

export function usePaperArena() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  useEffect(() => {
    let mounted = true

    async function fetchData() {
      try {
        const r = await fetch(PAPER_ARENA_URL, { cache: "no-store" })
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const json = await r.json()
        if (mounted) {
          setData(json)
          setLastUpdated(new Date())
          setLoading(false)
          setError(null)
        }
      } catch (e) {
        if (mounted) {
          setError(e.message)
          setLoading(false)
        }
      }
    }

    fetchData()
    const interval = setInterval(fetchData, POLL_INTERVAL_MS)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  const isPaperMode = data?.mode === "PAPER_SANDBOX_NO_REAL_CAPITAL" || data?.mode === "PAPER_CHAMPIONSHIP" || data?.mode_legacy === "PAPER_SANDBOX_NO_REAL_CAPITAL"

  return { data, loading, error, isPaperMode, lastUpdated }
}
