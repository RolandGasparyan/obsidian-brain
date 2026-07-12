import { useEffect, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"

// Spawns tiny upward particles on 'qwr:fx' win/bigwin events.
let seq = 0

export default function ParticleDrift() {
  const [burst, setBurst] = useState([])

  useEffect(() => {
    const onFx = (ev) => {
      const e = ev.detail
      if (e.type !== "win" && e.type !== "bigwin") return
      const count = e.type === "bigwin" ? 18 : 7
      const id = ++seq
      const parts = Array.from({ length: count }, (_, i) => ({
        id: `${id}-${i}`,
        x: 40 + Math.random() * 20,   // centered band
        dx: (Math.random() - 0.5) * 40,
        dy: -60 - Math.random() * 80,
        size: 2 + Math.random() * 3,
        delay: Math.random() * 0.15,
      }))
      setBurst(b => [...b, { id, parts }])
      setTimeout(() => setBurst(b => b.filter(x => x.id !== id)), 1400)
    }
    window.addEventListener("qwr:fx", onFx)
    return () => window.removeEventListener("qwr:fx", onFx)
  }, [])

  return (
    <div className="fixed inset-0 pointer-events-none z-[55]">
      <AnimatePresence>
        {burst.flatMap(b => b.parts.map(p => (
          <motion.span
            key={p.id}
            initial={{ opacity: 0, y: 0, x: 0, scale: 0.6 }}
            animate={{ opacity: [0, 0.9, 0], y: p.dy, x: p.dx, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.1, delay: p.delay, ease: "easeOut" }}
            style={{
              position: "absolute",
              left: `${p.x}%`,
              bottom: "12%",
              width: p.size,
              height: p.size,
              borderRadius: "9999px",
              background: "rgba(52,211,153,0.85)",
              boxShadow: "0 0 8px rgba(52,211,153,0.7)",
            }}
          />
        )))}
      </AnimatePresence>
    </div>
  )
}
