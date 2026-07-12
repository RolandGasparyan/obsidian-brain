import { useEffect, useMemo, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { audio } from "../ui/audio_engine.js"
import { useApp } from "../state/AppContext.jsx"

export default function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState("")
  const [sel, setSel] = useState(0)
  const { prefs, setPref, dispatch } = useApp()

  const commands = useMemo(() => [
    { id: "sound",   label: prefs.sound  ? "Disable Sound FX" : "Enable Sound FX",
      run: () => setPref("sound", !prefs.sound) },
    { id: "threeD",  label: prefs.threeD ? "Hide 3D Background" : "Show 3D Background",
      run: () => setPref("threeD", !prefs.threeD) },
    { id: "reduced", label: prefs.reducedMotion ? "Disable Reduced Motion" : "Enable Reduced Motion",
      run: () => setPref("reducedMotion", !prefs.reducedMotion) },
    { id: "intro",   label: "Replay Cinematic Intro",
      run: () => location.reload() },
    { id: "win",     label: "Simulate Trade — Small Win (+$12)",
      run: () => dispatch({ type: "trade", pnl: 12 }) },
    { id: "big",     label: "Simulate Trade — Big Win (+$120)",
      run: () => dispatch({ type: "trade", pnl: 120 }) },
    { id: "loss",    label: "Simulate Trade — Loss (−$18)",
      run: () => dispatch({ type: "trade", pnl: -18 }) },
    { id: "dd",      label: "Simulate Drawdown Spike (−$180)",
      run: () => dispatch({ type: "trade", pnl: -180 }) },
  ], [prefs])

  const filtered = commands.filter(c =>
    c.label.toLowerCase().includes(q.toLowerCase())
  )

  useEffect(() => {
    const onKey = (e) => {
      const isCmd = e.metaKey || e.ctrlKey
      if (isCmd && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setOpen(o => !o)
        setQ("")
        setSel(0)
        audio.click()
      } else if (open && e.key === "Escape") {
        setOpen(false)
      } else if (open && e.key === "ArrowDown") {
        setSel(s => Math.min(s + 1, filtered.length - 1))
      } else if (open && e.key === "ArrowUp") {
        setSel(s => Math.max(s - 1, 0))
      } else if (open && e.key === "Enter") {
        const c = filtered[sel]
        if (c) { c.run(); audio.click(); setOpen(false) }
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, filtered, sel])

  return (
    <>
      {/* Hint chip */}
      <motion.button
        onClick={() => { audio.click(); setOpen(true) }}
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.96 }}
        className="fixed top-4 left-4 z-40 flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-black/60 backdrop-blur text-[11px] uppercase tracking-[0.2em] text-white/60 hover:text-white"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400/80" />
        <span>Command</span>
        <kbd className="font-mono text-white/40 text-[10px]">⌘K</kbd>
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[16vh]"
            onClick={() => setOpen(false)}
          >
            <motion.div
              onClick={e => e.stopPropagation()}
              initial={{ y: -20, scale: 0.95, opacity: 0 }}
              animate={{ y: 0,  scale: 1,   opacity: 1 }}
              exit={{    y: -20, scale: 0.95, opacity: 0 }}
              transition={{ type: "spring", stiffness: 320, damping: 28 }}
              className="w-[520px] max-w-[92vw] rounded-2xl border border-white/10 bg-[#0a0a0a]/95 shadow-2xl overflow-hidden"
            >
              <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10">
                <span className="text-white/40 text-sm">⌘K</span>
                <input
                  autoFocus
                  value={q}
                  onChange={e => { setQ(e.target.value); setSel(0) }}
                  placeholder="Search actions…"
                  className="flex-1 bg-transparent outline-none text-sm placeholder:text-white/30"
                />
                <span className="text-[10px] uppercase tracking-[0.2em] text-white/30">
                  {filtered.length}
                </span>
              </div>
              <div className="max-h-[50vh] overflow-y-auto">
                {filtered.length === 0 && (
                  <div className="p-6 text-sm text-white/40 text-center">No matches</div>
                )}
                {filtered.map((c, i) => (
                  <button
                    key={c.id}
                    onClick={() => { c.run(); audio.click(); setOpen(false) }}
                    onMouseEnter={() => setSel(i)}
                    className={
                      "w-full text-left px-4 py-2.5 text-sm flex items-center gap-3 transition-colors " +
                      (i === sel ? "bg-emerald-400/10 text-white" : "text-white/70 hover:bg-white/5")
                    }
                  >
                    <span className="w-1 h-5 rounded-full" style={{
                      background: i === sel ? "#34d399" : "transparent"
                    }} />
                    <span>{c.label}</span>
                  </button>
                ))}
              </div>
              <div className="px-4 py-2 border-t border-white/10 text-[10px] uppercase tracking-[0.2em] text-white/30 flex justify-between">
                <span>↑↓ Navigate</span>
                <span>↵ Select</span>
                <span>ESC Close</span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
