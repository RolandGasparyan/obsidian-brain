import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { audio } from "../ui/audio_engine.js"
import { AGENTS } from "./AgentSprites.jsx"

const STORAGE_KEY = "qwr.bets.v1"

export function getBets() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]") } catch { return [] }
}
export function saveBets(list) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  window.dispatchEvent(new CustomEvent("qwr:bets", { detail: list }))
}

// Deterministic odds table based on agent position — lower ROI → higher odds
const DEFAULT_ODDS = {
  champion: 2.1,
  executor: 2.4,
  alpha:    3.1,
  hunter:   3.8,
  regime:   4.5,
  skeptic:  6.2,
  risk:     7.8,
  recovery: 12.0,
}

export default function BetModal({ open, onClose }) {
  const [picked, setPicked] = useState(null)
  const [stake, setStake]   = useState("100")
  const [phase, setPhase]   = useState("pick")   // pick | confirm | placed
  const [bet, setBet]       = useState(null)

  useEffect(() => {
    if (!open) { setPicked(null); setStake("100"); setPhase("pick"); setBet(null) }
  }, [open])

  const place = () => {
    if (!picked || !stake || +stake < 10) return
    audio.click?.()
    const odds = DEFAULT_ODDS[picked.id] || 3.0
    const payout = +stake * odds
    const newBet = {
      id: Date.now(),
      agentId: picked.id,
      agentName: picked.name,
      color: picked.color,
      stake: +stake,
      odds,
      payout,
      placedAt: Date.now(),
      status: "active",
    }
    saveBets([...getBets(), newBet])
    setBet(newBet)
    setPhase("placed")
    audio.triumph?.()
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-[120] bg-black/70 backdrop-blur-md flex items-center justify-center p-4"
        >
          <motion.div
            onClick={e => e.stopPropagation()}
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1,   y: 0 }}
            exit={{    opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 300, damping: 28 }}
            className="qwr-panel w-[600px] max-w-[96vw] max-h-[88vh] overflow-y-auto p-5 relative"
            style={{ boxShadow: "0 0 30px rgba(255,255,0,0.35)" }}
          >
            <button
              onClick={() => { audio.click?.(); onClose() }}
              className="absolute top-3 right-3 pk text-[10px] text-[color:var(--subdim)] hover:text-[color:var(--text)] tracking-widest"
            >✕ CLOSE</button>

            <div
              className="pk text-sm tracking-widest mb-4"
              style={{ color: "#ffff00", textShadow: "0 0 8px rgba(255,255,0,0.6)" }}
            >★ PLACE BET — RACE TO $1M</div>

            {/* Pick phase */}
            {phase === "pick" && (
              <>
                <div className="mono text-[11px] text-[color:var(--subdim)] mb-3">
                  Pick the agent you think will reach $1,000,000 first. Higher odds = longer shot.
                </div>
                <div className="space-y-2">
                  {AGENTS.map(a => {
                    const odds = DEFAULT_ODDS[a.id] || 3.0
                    const isPicked = picked?.id === a.id
                    return (
                      <motion.button
                        key={a.id}
                        whileHover={{ x: 2 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => { audio.click?.(); setPicked(a) }}
                        className="w-full flex items-center gap-3 p-3 border text-left"
                        style={{
                          borderColor: isPicked ? a.color : "var(--border)",
                          background: isPicked ? a.color + "18" : "rgba(11,21,37,0.3)",
                          boxShadow: isPicked ? `0 0 12px ${a.color}66` : "none",
                        }}
                      >
                        <div className="w-10 h-10 flex items-center justify-center"
                             style={{ border: `1px solid ${a.color}`, background: a.color + "22" }}>
                          <a.Sprite size={28} color={a.color} />
                        </div>
                        <div className="flex-1">
                          <div className="pk text-[11px]" style={{ color: a.color }}>{a.name}</div>
                          <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mt-1">{a.role}</div>
                        </div>
                        <div className="text-right">
                          <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)]">ODDS</div>
                          <div
                            className="pk text-base"
                            style={{ color: "#ffff00", textShadow: "0 0 4px rgba(255,255,0,0.5)" }}
                          >
                            {odds.toFixed(2)}x
                          </div>
                        </div>
                      </motion.button>
                    )
                  })}
                </div>
                {picked && (
                  <motion.button
                    initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                    onClick={() => setPhase("confirm")}
                    className="w-full pk text-sm tracking-widest px-4 py-3 border mt-4"
                    style={{
                      color: picked.color,
                      borderColor: picked.color,
                      background: picked.color + "15",
                      boxShadow: `0 0 14px ${picked.color}55`,
                    }}
                  >
                    ► BET ON {picked.name}
                  </motion.button>
                )}
              </>
            )}

            {/* Confirm phase */}
            {phase === "confirm" && picked && (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 border"
                     style={{ borderColor: picked.color, background: picked.color + "12" }}>
                  <div className="w-12 h-12 flex items-center justify-center"
                       style={{ border: `1px solid ${picked.color}`, background: picked.color + "22" }}>
                    <picked.Sprite size={36} color={picked.color} />
                  </div>
                  <div className="flex-1">
                    <div className="pk text-[12px]" style={{ color: picked.color }}>{picked.name}</div>
                    <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mt-1">{picked.role}</div>
                  </div>
                  <div
                    className="pk text-lg"
                    style={{ color: "#ffff00", textShadow: "0 0 6px rgba(255,255,0,0.5)" }}
                  >
                    {(DEFAULT_ODDS[picked.id] || 3.0).toFixed(2)}x
                  </div>
                </div>

                <div>
                  <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mb-1">STAKE (USDT)</div>
                  <div className="flex items-center gap-2 border p-2" style={{ borderColor: "#ffff0055", background: "rgba(11,21,37,0.5)" }}>
                    <span className="pk text-base text-[color:var(--yellow)]">$</span>
                    <input
                      type="number"
                      value={stake}
                      onChange={e => setStake(e.target.value)}
                      min={10}
                      className="flex-1 bg-transparent outline-none pk text-lg text-[color:var(--yellow)]"
                    />
                  </div>
                  <div className="flex gap-2 flex-wrap mt-2">
                    {[10, 50, 100, 500, 1000].map(v => (
                      <button
                        key={v}
                        onClick={() => { audio.click?.(); setStake(String(v)) }}
                        className="pk text-[9px] tracking-widest px-3 py-1 border"
                        style={{ color: "#ffff00", borderColor: "#ffff0044", background: "rgba(11,21,37,0.4)" }}
                      >${v}</button>
                    ))}
                  </div>
                </div>

                <div className="p-3 border" style={{ borderColor: "#00ff4155", background: "rgba(0,255,65,0.06)" }}>
                  <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mb-1">POTENTIAL PAYOUT</div>
                  <div className="pk text-2xl" style={{ color: "#00ff41", textShadow: "0 0 10px rgba(0,255,65,0.6)" }}>
                    ${(+stake * (DEFAULT_ODDS[picked.id] || 3.0)).toFixed(2)}
                  </div>
                  <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mt-1">
                    STAKE ${(+stake).toFixed(2)} × {(DEFAULT_ODDS[picked.id] || 3.0).toFixed(2)}x
                  </div>
                </div>

                <div className="flex gap-2">
                  <motion.button
                    whileHover={{ scale: 1.03 }}
                    onClick={() => setPhase("pick")}
                    className="flex-1 pk text-[10px] tracking-widest px-4 py-3 border"
                    style={{ color: "var(--subdim)", borderColor: "var(--border)" }}
                  >◄ BACK</motion.button>
                  <motion.button
                    whileHover={{ scale: 1.03 }}
                    onClick={place}
                    disabled={+stake < 10}
                    className="flex-1 pk text-sm tracking-widest px-4 py-3 border"
                    style={{
                      color: +stake >= 10 ? "#ffff00" : "var(--subdim)",
                      borderColor: +stake >= 10 ? "#ffff00" : "var(--border)",
                      background: +stake >= 10 ? "rgba(255,255,0,0.12)" : "transparent",
                      boxShadow: +stake >= 10 ? "0 0 14px rgba(255,255,0,0.5)" : "none",
                    }}
                  >PLACE BET ►</motion.button>
                </div>
              </div>
            )}

            {/* Placed confirmation */}
            {phase === "placed" && bet && (
              <div className="py-6 text-center space-y-3">
                <div style={{ fontSize: 56 }}>🎟</div>
                <div
                  className="pk text-lg tracking-widest"
                  style={{ color: "#ffff00", textShadow: "0 0 12px rgba(255,255,0,0.7)" }}
                >BET PLACED</div>
                <div className="mono text-[11px] text-[color:var(--text)]">
                  ${bet.stake} on <span style={{ color: bet.color }}>{bet.agentName}</span> @ {bet.odds.toFixed(2)}x
                </div>
                <div
                  className="pk text-sm"
                  style={{ color: "#00ff41", textShadow: "0 0 8px rgba(0,255,65,0.6)" }}
                >
                  POTENTIAL WIN: ${bet.payout.toFixed(2)}
                </div>
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  onClick={() => { audio.click?.(); onClose() }}
                  className="pk text-[10px] tracking-widest px-6 py-2 border mt-3"
                  style={{ color: "#ffff00", borderColor: "#ffff00", background: "rgba(255,255,0,0.1)" }}
                >CONTINUE ►</motion.button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
