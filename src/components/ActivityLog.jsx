import { useEffect, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import InteractiveCard from "./InteractiveCard.jsx"
import { AGENTS } from "./AgentSprites.jsx"

const MAX_LINES = 12

const CHATTER = [
  (a) => `${a.name} scans orderbook · spread ${(Math.random()*0.05).toFixed(3)}%`,
  (a) => `${a.name} votes BUY · conviction ${(40 + Math.random()*55).toFixed(0)}%`,
  (a) => `${a.name} rejects thesis · R:R below 1.0`,
  (a) => `${a.name} detects momentum expansion on ${["BTC","ETH","SOL","BNB"][Math.floor(Math.random()*4)]}`,
  (a) => `${a.name} flags risk · exposure ${(Math.random()*30+10).toFixed(1)}%`,
  (a) => `${a.name} trails stop to break-even`,
  (a) => `${a.name} measures ATR ${(Math.random()*2+0.5).toFixed(2)}%`,
  (a) => `${a.name} relays signal to EXECUTOR`,
  (a) => `${a.name} regime snapshot · ${["TRENDING","NEUTRAL","SQUEEZE"][Math.floor(Math.random()*3)]}`,
  (a) => `${a.name} hedge rebalance initiated`,
]

function mkId() { return Math.random().toString(36).slice(2, 9) }

export default function ActivityLog({ activeAgent }) {
  const [lines, setLines] = useState([])
  const endRef = useRef(null)

  // Inject agent chatter
  useEffect(() => {
    const t = setInterval(() => {
      const a = AGENTS[Math.floor(Math.random()*AGENTS.length)]
      const msg = CHATTER[Math.floor(Math.random()*CHATTER.length)](a)
      setLines(ls => [...ls.slice(-(MAX_LINES-1)), {
        id: mkId(), ts: new Date(), kind: "chatter", msg, color: a.color, agentId: a.id,
      }])
    }, 1800 + Math.random()*1400)
    return () => clearInterval(t)
  }, [])

  // Listen for trade FX events → log trade entries
  useEffect(() => {
    const onFx = (ev) => {
      const e = ev.detail
      const kind = e.type
      const label = {
        win:    ["TRADE CLOSED",  "#00ff41", `+$${e.magnitude.toFixed(2)} · WIN`],
        bigwin: ["★ BIG WIN ★",  "#ffff00", `+$${e.magnitude.toFixed(2)} · TP3 hit`],
        loss:   ["TRADE CLOSED",  "#ff3333", `-$${e.magnitude.toFixed(2)} · stop`],
        dd:     ["DRAWDOWN SPIKE","#ff8800", `-$${e.magnitude.toFixed(2)} · risk alert`],
      }[kind] || ["EVENT", "#c0ddf0", kind]
      setLines(ls => [...ls.slice(-(MAX_LINES-1)), {
        id: mkId(), ts: new Date(), kind: "event",
        msg: `${label[0]} · ${label[2]}`,
        color: label[1],
      }])
    }
    window.addEventListener("qwr:fx", onFx)
    return () => window.removeEventListener("qwr:fx", onFx)
  }, [])

  // Auto-scroll only inside the log container (never bubbles to page)
  useEffect(() => {
    const el = endRef.current?.parentElement
    if (el) el.scrollTop = el.scrollHeight
  }, [lines.length])

  const activeColor = AGENTS.find(a => a.id === activeAgent)?.color || "#00ff41"

  return (
    <InteractiveCard
      title="LIVE ACTIVITY LOG"
      tooltip="Real-time stream of agent chatter, votes, and trade events"
      accent={activeColor}
    >
      <div
        className="h-32 overflow-y-auto pr-1 mono text-[10px] leading-[1.5] border border-[color:var(--border)] p-2"
        style={{
          background: "rgba(11,21,37,0.35)",
          backdropFilter: "blur(4px)",
          WebkitBackdropFilter: "blur(4px)",
          boxShadow: "inset 0 0 20px rgba(0,255,65,0.04)",
          overflowAnchor: "none",
          overscrollBehavior: "contain",
        }}
      >
        <AnimatePresence initial={false}>
          {lines.map(line => (
            <motion.div
              key={line.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="flex items-baseline gap-2"
            >
              <span className="text-[color:var(--subdim)] select-none">
                {line.ts.toTimeString().slice(0,8)}
              </span>
              <span className="text-[color:var(--subdim)]">│</span>
              <span style={{ color: line.color, textShadow: `0 0 4px ${line.color}44` }}>
                {line.kind === "event" ? "◆" : "▸"} {line.msg}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={endRef} />
      </div>
      <div className="mt-2 flex items-center justify-between pk text-[7px] text-[color:var(--subdim)] tracking-widest">
        <span>{lines.length} ENTRIES</span>
        <span style={{ color: "var(--green)", animation: "qwr-blink 1.1s infinite" }}>● STREAMING</span>
      </div>
    </InteractiveCard>
  )
}
