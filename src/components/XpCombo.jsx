import { useEffect, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { useApp } from "../state/AppContext.jsx"

// Gamified header bauble: level + XP bar + combo counter
export default function XpCombo() {
  const { state } = useApp()
  const [xp, setXp]       = useState(0)
  const [level, setLevel] = useState(1)
  const [combo, setCombo] = useState(0)
  const [flash, setFlash] = useState(0)

  useEffect(() => {
    const onFx = (ev) => {
      const e = ev.detail
      if (e.type === "win" || e.type === "bigwin") {
        const gain = e.type === "bigwin" ? 140 : 30
        setXp(x => {
          const nx = x + gain
          const lvlXp = level * 250
          if (nx >= lvlXp) { setLevel(l => l + 1); return nx - lvlXp }
          return nx
        })
        setCombo(c => c + 1)
        setFlash(f => f + 1)
      } else if (e.type === "loss" || e.type === "dd") {
        setCombo(0)
      }
    }
    window.addEventListener("qwr:fx", onFx)
    return () => window.removeEventListener("qwr:fx", onFx)
  }, [level])

  const lvlXp = level * 250
  const pct = Math.min(1, xp / lvlXp)

  return (
    <div className="flex items-center gap-4">
      <motion.div
        animate={flash > 0 ? { scale: [1, 1.15, 1] } : {}}
        transition={{ duration: 0.5 }}
        className="flex items-center gap-2 px-2 py-1 border border-[color:var(--border)] bg-[color:var(--panel)]"
        style={{ boxShadow: "0 0 10px rgba(0,255,255,0.15)" }}
      >
        <span className="pk text-[7px] text-[color:var(--cyan)] tracking-widest">LVL</span>
        <span
          className="pk text-[14px] text-[color:var(--cyan)]"
          style={{ textShadow: "0 0 6px rgba(0,255,255,0.6)" }}
        >
          {level}
        </span>
      </motion.div>

      <div className="flex flex-col gap-1 w-40">
        <div className="flex items-center justify-between pk text-[6px] tracking-widest text-[color:var(--subdim)]">
          <span>XP</span>
          <span>{xp} / {lvlXp}</span>
        </div>
        <div className="h-1.5 border border-[color:var(--border)] bg-[color:var(--panel)] overflow-hidden relative">
          <motion.div
            className="h-full"
            style={{
              background: "linear-gradient(90deg, var(--cyan), var(--green))",
              boxShadow: "0 0 6px var(--cyan)",
            }}
            animate={{ width: `${pct*100}%` }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
          {/* animated shimmer sweep */}
          <div
            className="absolute inset-y-0 w-1/3"
            style={{
              background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.28), transparent)",
              animation: "qwr-shimmer 2.4s ease-in-out infinite",
            }}
          />
        </div>
      </div>

      <AnimatePresence>
        {combo >= 2 && (
          <motion.div
            key={combo}
            initial={{ opacity: 0, scale: 0.6, rotate: -8 }}
            animate={{ opacity: 1, scale: 1,   rotate: 0 }}
            exit={{    opacity: 0, scale: 0.4, rotate: 8 }}
            transition={{ type: "spring", stiffness: 400, damping: 20 }}
            className="pk text-[14px] px-2 py-1 border"
            style={{
              color: "var(--yellow)",
              borderColor: "var(--yellow)",
              background: "rgba(255,255,0,0.08)",
              textShadow: "0 0 8px rgba(255,255,0,0.7)",
              boxShadow: "0 0 12px rgba(255,255,0,0.35)",
            }}
          >
            x{combo} COMBO!
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
