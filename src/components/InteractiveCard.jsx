import { useRef, useState } from "react"
import { motion, AnimatePresence, useMotionValue, useSpring, useTransform } from "framer-motion"
import { audio } from "../ui/audio_engine.js"
import { useApp } from "../state/AppContext.jsx"

export default function InteractiveCard({
  title,
  tooltip,
  children,
  expanded,
  className = "",
  accent = "#00ff41",
}) {
  const { prefs } = useApp()
  const [open, setOpen] = useState(false)
  const [hover, setHover] = useState(false)
  const ref = useRef(null)
  const intensity = prefs.intensity
  const reduced   = prefs.reducedMotion

  // Mouse-tilt parallax
  const mx = useMotionValue(0.5)
  const my = useMotionValue(0.5)
  const sx = useSpring(mx, { stiffness: 200, damping: 20 })
  const sy = useSpring(my, { stiffness: 200, damping: 20 })
  const rotX = useTransform(sy, [0, 1], [ 3 * intensity, -3 * intensity])
  const rotY = useTransform(sx, [0, 1], [-5 * intensity,  5 * intensity])

  const onMove = (e) => {
    if (reduced || !ref.current) return
    const r = ref.current.getBoundingClientRect()
    mx.set((e.clientX - r.left) / r.width)
    my.set((e.clientY - r.top)  / r.height)
  }
  const onLeave = () => { mx.set(0.5); my.set(0.5); setHover(false) }

  return (
    <motion.div
      ref={ref}
      whileHover={{ y: -2 * intensity }}
      transition={{ type: "spring", stiffness: 260, damping: 22 }}
      onHoverStart={() => { setHover(true); audio.hover?.() }}
      onHoverEnd={onLeave}
      onMouseMove={onMove}
      onClick={() => { if (expanded) { audio.click(); setOpen(o => !o) } }}
      style={{
        rotateX: reduced ? 0 : rotX,
        rotateY: reduced ? 0 : rotY,
        transformPerspective: 900,
        transformStyle: "preserve-3d",
        borderColor: hover ? accent : undefined,
        boxShadow: hover ? `0 0 0 1px ${accent}44, 0 0 24px -8px ${accent}88` : undefined,
      }}
      className={
        "relative p-4 qwr-panel cursor-" + (expanded ? "pointer" : "default") +
        " overflow-hidden select-none transition-colors " + className
      }
    >
      {/* shimmer sweep on hover */}
      {!reduced && hover && (
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div
            className="absolute -inset-y-1 w-1/3"
            style={{
              background: `linear-gradient(90deg, transparent, ${accent}18, transparent)`,
              animation: "qwr-shimmer 1.1s ease",
            }}
          />
        </div>
      )}

      {title && (
        <div className="relative flex items-center justify-between pk text-[8px] text-[color:var(--subdim)] mb-3">
          <span className="inline-flex items-center gap-2">
            <span className="w-1.5 h-1.5" style={{ background: accent, boxShadow: `0 0 6px ${accent}` }} />
            {title}
          </span>
          {tooltip && <span title={tooltip} className="text-[color:var(--subdim)] hover:text-[color:var(--text)]">[?]</span>}
        </div>
      )}
      <div className="relative">{children}</div>
      <AnimatePresence>
        {open && expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: "easeOut" }}
            className="relative mt-3 pt-3 border-t border-dashed border-[color:var(--border)] text-[11px] text-[color:var(--subdim)] overflow-hidden"
          >
            {expanded}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
