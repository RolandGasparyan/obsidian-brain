import { useEffect, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"

// Screen-level overlays reacting to "qwr:fx" custom events dispatched by useEventFX.
export default function EventEffects() {
  const [flash, setFlash] = useState(null)   // { type, id }
  const [shakeId, setShakeId] = useState(0)

  useEffect(() => {
    const onFx = (ev) => {
      const e = ev.detail
      const id = e.ts
      setFlash({ type: e.type, id })
      if (e.type === "loss") setShakeId(s => s + 1)
      setTimeout(() => setFlash(f => (f && f.id === id ? null : f)), 700)
    }
    window.addEventListener("qwr:fx", onFx)
    return () => window.removeEventListener("qwr:fx", onFx)
  }, [])

  // Micro shake on loss — apply translate on <body> via CSS var
  useEffect(() => {
    if (!shakeId) return
    const root = document.documentElement
    root.style.setProperty("--qwr-shake", "1")
    const t = setTimeout(() => root.style.setProperty("--qwr-shake", "0"), 380)
    return () => clearTimeout(t)
  }, [shakeId])

  const color = {
    win:    "rgba(16,185,129,0.18)",   // emerald
    bigwin: "rgba(16,185,129,0.30)",
    loss:   "rgba(244,63,94,0.14)",    // rose
    dd:     "rgba(234,179,8,0.16)",    // amber — drawdown warning
  }[flash?.type] || "transparent"

  return (
    <>
      {/* Screen flash overlay */}
      <AnimatePresence>
        {flash && (
          <motion.div
            key={flash.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="fixed inset-0 pointer-events-none z-[60]"
            style={{
              background: `radial-gradient(circle at 50% 50%, ${color} 0%, transparent 70%)`,
              mixBlendMode: "screen",
            }}
          />
        )}
      </AnimatePresence>

      {/* Edge pulse for drawdown spike */}
      <AnimatePresence>
        {flash?.type === "dd" && (
          <motion.div
            key={"dd-"+flash.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.8, 0] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.9 }}
            className="fixed inset-0 pointer-events-none z-[61]"
            style={{
              boxShadow: "inset 0 0 120px 8px rgba(234,179,8,0.35)",
            }}
          />
        )}
      </AnimatePresence>

      {/* Big win particle ripple */}
      <AnimatePresence>
        {flash?.type === "bigwin" && (
          <motion.div
            key={"bw-"+flash.id}
            initial={{ scale: 0, opacity: 0.6 }}
            animate={{ scale: 4.5, opacity: 0 }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[62] pointer-events-none"
          >
            <div className="w-24 h-24 rounded-full border-2 border-emerald-400/60" />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
