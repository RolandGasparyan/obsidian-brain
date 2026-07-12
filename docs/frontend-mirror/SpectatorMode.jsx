/**
 * SpectatorMode.jsx — Global toggle that hides dev panels for clean spectator view.
 *
 * When active, adds `body.spectator-mode` class. CSS rules in arena-overrides.css
 * hide non-essential panels (paper showcase, agent telemetry, cycle panel, etc.)
 * leaving only the cinematic core (overlay + commentary + rivalry).
 *
 * - Floating toggle button bottom-left (always visible)
 * - Hotkey 'S' to toggle
 * - State persists in localStorage
 *
 * Phase 12 · 2026-05-13 · Layer 3 UX polish
 */
import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { audio } from "../ui/audio_engine.js"

const STORAGE_KEY = "tradingguru.spectatorMode"

export default function SpectatorMode() {
  const [active, setActive] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) === "1" } catch { return false }
  })

  // Sync body class + storage on state change
  useEffect(() => {
    if (active) document.body.classList.add("spectator-mode")
    else        document.body.classList.remove("spectator-mode")
    try { localStorage.setItem(STORAGE_KEY, active ? "1" : "0") } catch {}
  }, [active])

  // Hotkey: S
  useEffect(() => {
    const onKey = (e) => {
      // Ignore if typing in input/textarea
      const tag = (e.target?.tagName || "").toLowerCase()
      if (tag === "input" || tag === "textarea") return
      if (e.key === "s" || e.key === "S") {
        setActive(v => !v)
        audio.click?.()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  return (
    <motion.button
      onClick={() => { setActive(v => !v); audio.click?.() }}
      whileHover={{ scale: 1.04 }}
      whileTap={{ scale: 0.96 }}
      className="fixed bottom-4 left-4 pk text-[9px] tracking-widest px-3 py-2 mono"
      title="Toggle spectator mode (S)"
      style={{
        zIndex: 60,
        background: active ? "var(--accent-yellow)" : "rgba(8,15,30,0.85)",
        color: active ? "var(--bg)" : "var(--accent-yellow)",
        border: "1px solid var(--accent-yellow)",
        borderRadius: 4,
        cursor: "pointer",
        boxShadow: active
          ? "0 0 14px -2px var(--accent-yellow)"
          : "0 0 8px -4px var(--accent-yellow)",
      }}
    >
      {active ? "🎬 SPECTATOR · ON" : "👁 SPECTATOR · OFF"}
      <span className="ml-2 text-[7px]" style={{ opacity: 0.7 }}>(S)</span>
    </motion.button>
  )
}
