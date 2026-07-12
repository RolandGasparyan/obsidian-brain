import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { audio } from "../ui/audio_engine.js"
import { useApp } from "../state/AppContext.jsx"

function Toggle({ label, value, onChange }) {
  return (
    <button
      onClick={() => { audio.click(); onChange(!value) }}
      className="flex items-center justify-between w-full py-2 text-sm"
    >
      <span className="text-white/70">{label}</span>
      <span className={
        "relative w-10 h-5 rounded-full transition-colors " +
        (value ? "bg-emerald-500/80" : "bg-white/10")
      }>
        <motion.span
          layout
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
          className={
            "absolute top-0.5 h-4 w-4 rounded-full bg-white " +
            (value ? "right-0.5" : "left-0.5")
          }
        />
      </span>
    </button>
  )
}

function Slider({ label, value, onChange }) {
  return (
    <div className="py-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-white/70">{label}</span>
        <span className="text-white/50 text-xs">{Math.round(value*100)}%</span>
      </div>
      <input
        type="range" min="0" max="1" step="0.05"
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-full accent-emerald-400 mt-1"
      />
    </div>
  )
}

export default function SettingsPanel() {
  const { prefs, setPref } = useApp()
  const [open, setOpen] = useState(false)

  return (
    <>
      <motion.button
        whileHover={{ rotate: 45 }}
        whileTap={{ scale: 0.92 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
        onClick={() => { audio.click(); setOpen(o => !o) }}
        className="fixed top-4 right-4 z-50 w-9 h-9 rounded-full border border-white/10 bg-black/60 backdrop-blur text-white/60 hover:text-white flex items-center justify-center"
        aria-label="Settings"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, x: 20, scale: 0.98 }}
            animate={{ opacity: 1, x: 0,  scale: 1 }}
            exit={{    opacity: 0, x: 20, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 300, damping: 28 }}
            className="fixed top-16 right-4 z-50 w-72 rounded-2xl border border-white/10 bg-black/80 backdrop-blur-xl p-5 shadow-2xl"
          >
            <div className="text-[11px] uppercase tracking-[0.2em] text-white/40 mb-3">
              Display & Audio
            </div>
            <Toggle label="Sound FX"           value={prefs.sound}         onChange={v => setPref("sound", v)} />
            <Toggle label="3D Background"      value={prefs.threeD}        onChange={v => setPref("threeD", v)} />
            <Toggle label="Reduced Motion"     value={prefs.reducedMotion} onChange={v => setPref("reducedMotion", v)} />
            <Slider label="Animation Intensity" value={prefs.intensity}    onChange={v => setPref("intensity", v)} />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
