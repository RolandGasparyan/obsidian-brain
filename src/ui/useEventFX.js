import { useEffect, useRef } from "react"
import { audio, setEnabled } from "./audio_engine.js"
import { useApp } from "../state/AppContext.jsx"

// Reacts to state.lastEvent — plays sound + dispatches CSS effect class on <body>
export function useEventFX() {
  const { state, prefs } = useApp()
  const lastTs = useRef(0)

  useEffect(() => { setEnabled(prefs.sound) }, [prefs.sound])

  useEffect(() => {
    const e = state.lastEvent
    if (!e || e.ts === lastTs.current) return
    lastTs.current = e.ts

    // Audio
    if      (e.type === "bigwin") audio.bigWin()
    else if (e.type === "win")    audio.win()
    else if (e.type === "loss")   audio.loss()
    else if (e.type === "dd")     audio.warning()

    // Visual — body-level flash (CSS picks it up from App.jsx overlay listeners)
    window.dispatchEvent(new CustomEvent("qwr:fx", { detail: e }))
  }, [state.lastEvent])
}
