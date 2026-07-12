import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { audio } from "../ui/audio_engine.js"

export default function ActionModal({ open, onClose, title, color = "#00ff41", children }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-[120] bg-black/70 backdrop-blur-md flex items-center justify-center p-4"
        >
          <motion.div
            onClick={e => e.stopPropagation()}
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1,   y: 0 }}
            exit={{    opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 300, damping: 28 }}
            className="qwr-panel w-[520px] max-w-[96vw] max-h-[88vh] overflow-y-auto p-5 relative"
            style={{ boxShadow: `0 0 0 1px ${color}44, 0 0 30px -10px ${color}88` }}
          >
            <button
              onClick={() => { audio.click?.(); onClose() }}
              className="absolute top-3 right-3 pk text-[10px] text-[color:var(--subdim)] hover:text-[color:var(--text)] tracking-widest"
            >
              ✕ CLOSE
            </button>
            <div
              className="pk text-sm tracking-widest mb-4"
              style={{ color, textShadow: `0 0 8px ${color}80` }}
            >
              ◆ {title}
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// Reusable content blocks
export function AmountInput({ label, value, setValue, min = 10, max = 100000, color = "#00ff41" }) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between pk text-[8px] tracking-widest text-[color:var(--subdim)]">
        <span>{label}</span>
        <span>MIN ${min} · MAX ${max.toLocaleString()}</span>
      </div>
      <div className="flex items-center gap-2 border p-2" style={{ borderColor: color + "55", background: "rgba(11,21,37,0.5)" }}>
        <span className="pk text-sm" style={{ color }}>$</span>
        <input
          type="number"
          value={value}
          onChange={e => setValue(e.target.value)}
          min={min}
          max={max}
          className="flex-1 bg-transparent outline-none pk text-lg"
          style={{ color, textShadow: `0 0 4px ${color}44` }}
        />
        <span className="pk text-[9px] tracking-widest text-[color:var(--subdim)]">USDT</span>
      </div>
      <div className="flex gap-2 flex-wrap">
        {[100, 500, 1000, 5000, 10000].map(v => (
          <button
            key={v}
            onClick={() => { audio.click?.(); setValue(String(v)) }}
            className="pk text-[9px] tracking-widest px-3 py-1 border"
            style={{
              color: color,
              borderColor: color + "44",
              background: "rgba(11,21,37,0.4)",
            }}
          >
            ${v}
          </button>
        ))}
      </div>
    </div>
  )
}

export function ConfirmButton({ label, color = "#00ff41", onClick, disabled }) {
  return (
    <motion.button
      whileHover={disabled ? {} : { scale: 1.03 }}
      whileTap={disabled ? {} : { scale: 0.97 }}
      onClick={onClick}
      disabled={disabled}
      className="w-full pk text-sm tracking-widest px-4 py-3 border mt-4"
      style={{
        color: disabled ? "var(--subdim)" : color,
        borderColor: disabled ? "var(--border)" : color,
        background: disabled ? "rgba(74,112,144,0.08)" : `${color}12`,
        boxShadow: disabled ? "none" : `0 0 16px ${color}44`,
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      ► {label}
    </motion.button>
  )
}
