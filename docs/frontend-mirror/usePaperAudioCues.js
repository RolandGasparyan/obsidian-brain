/**
 * usePaperAudioCues.js — Phase 11 audio cues for paper-arena events.
 *
 * Subscribes to usePaperArena().data.events and fires synthesized Web Audio
 * cues from audio_engine.js. All cues are subtle (existing engine volumes,
 * no new arcade noise) so the arena feels alive without overwhelming.
 *
 * Event → sound mapping:
 *   BIG_SIM_SWING (+pnl) → audio.bigWin()
 *   BIG_SIM_SWING (-pnl) → audio.loss()
 *   WIN_STREAK           → audio.win()
 *   LOSS_STREAK          → audio.warning()
 *   STATUS_CHANGE→STRIKING → audio.ping()
 *   PAPER CHAMPION CHANGE → audio.triumph()
 *
 * 2026-05-13 · Layer 3 audio · zero capital impact
 */
import { useEffect, useRef } from "react"
import { audio } from "../ui/audio_engine.js"
import { usePaperArena } from "./usePaperArena.js"

// Throttle: max 1 cue per type per 3s (prevent audio spam if engine bursts)
const COOLDOWN_MS = 3000

export function usePaperAudioCues({ enabled = true } = {}) {
  const { data: paperData, isPaperMode } = usePaperArena()
  const seenRef = useRef(new Set())
  const lastFireRef = useRef({})
  const lastChampionRef = useRef(null)

  // Fire on paper events
  useEffect(() => {
    if (!enabled || !isPaperMode || !paperData?.events) return
    const now = Date.now()
    for (const e of paperData.events) {
      const evId = `${e.type}:${e.agent_id}:${e.cycle}`
      if (seenRef.current.has(evId)) continue
      seenRef.current.add(evId)

      // Per-type cooldown
      const lastFire = lastFireRef.current[e.type] || 0
      if (now - lastFire < COOLDOWN_MS) continue

      try {
        if (e.type === "BIG_SIM_SWING") {
          if ((e.pnl_sim_usd || 0) > 0) audio.bigWin?.()
          else                          audio.loss?.()
          lastFireRef.current[e.type] = now
        } else if (e.type === "WIN_STREAK") {
          audio.win?.()
          lastFireRef.current[e.type] = now
        } else if (e.type === "LOSS_STREAK") {
          audio.warning?.()
          lastFireRef.current[e.type] = now
        } else if (e.type === "STATUS_CHANGE" && e.to === "STRIKING") {
          audio.ping?.()
          lastFireRef.current[e.type] = now
        }
      } catch {
        // audio engine errors are non-fatal
      }
    }
  }, [paperData, isPaperMode, enabled])

  // Fire on paper champion change (top of leaderboard shift)
  useEffect(() => {
    if (!enabled || !isPaperMode || !paperData?.agents?.length) return
    const top = [...paperData.agents].sort((a, b) =>
      (1200 + b.sharpe_sim * 200 + b.trades * 2 + b.win_rate * 100) -
      (1200 + a.sharpe_sim * 200 + a.trades * 2 + a.win_rate * 100)
    )[0]
    if (!top) return
    if (lastChampionRef.current && lastChampionRef.current !== top.label) {
      try { audio.triumph?.() } catch {}
    }
    lastChampionRef.current = top.label
  }, [paperData, isPaperMode, enabled])
}
