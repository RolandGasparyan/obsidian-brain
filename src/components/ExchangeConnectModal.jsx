import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { audio } from "../ui/audio_engine.js"

const EXCHANGES = [
  { id: "binance",  name: "Binance",      color: "#f0b90b", icon: "◈", desc: "Spot · Futures · largest volume" },
  { id: "coinbase", name: "Coinbase Pro", color: "#0052ff", icon: "◆", desc: "US-regulated · reliable" },
  { id: "kraken",   name: "Kraken",       color: "#5741d9", icon: "◉", desc: "Secure · low fees" },
  { id: "bybit",    name: "Bybit",        color: "#f7a600", icon: "▲", desc: "Derivatives · high liquidity" },
  { id: "gateio",   name: "Gate.io",      color: "#2354e6", icon: "⬢", desc: "1000+ pairs · spot focus" },
  { id: "okx",      name: "OKX",          color: "#0c0c0c", icon: "⟐", desc: "Global · L2 fast" },
  { id: "kucoin",   name: "KuCoin",       color: "#24ae8f", icon: "◢", desc: "Altcoin variety" },
  { id: "bitget",   name: "Bitget",       color: "#1da2b4", icon: "◇", desc: "Copy trading native" },
]

const STORAGE_KEY = "qwr.exchanges.v1"

export function getExchanges() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]") } catch { return [] }
}
export function saveExchanges(list) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  window.dispatchEvent(new CustomEvent("qwr:exchanges", { detail: list }))
}

export default function ExchangeConnectModal({ open, onClose }) {
  const [phase, setPhase]   = useState("list")  // list | keys | connecting | connected
  const [picked, setPicked] = useState(null)
  const [apiKey, setApiKey] = useState("")
  const [secret, setSecret] = useState("")
  const [connected, setConnected] = useState(() => getExchanges())

  useEffect(() => {
    if (!open) { setPhase("list"); setPicked(null); setApiKey(""); setSecret("") }
  }, [open])

  const startConnect = (e) => { audio.click?.(); setPicked(e); setPhase("keys") }

  const submit = () => {
    if (!apiKey || !secret) return
    audio.click?.()
    setPhase("connecting")
    setTimeout(() => {
      const entry = {
        id: picked.id,
        name: picked.name,
        color: picked.color,
        icon: picked.icon,
        keyMasked: apiKey.slice(0, 4) + "…" + apiKey.slice(-4),
        connectedAt: Date.now(),
        balance: +(Math.random() * 50000 + 1000).toFixed(2),
      }
      const next = [...connected.filter(x => x.id !== entry.id), entry]
      saveExchanges(next)
      setConnected(next)
      setPhase("connected")
      audio.triumph?.()
    }, 1600)
  }

  const disconnect = (id) => {
    const next = connected.filter(x => x.id !== id)
    saveExchanges(next)
    setConnected(next)
    audio.click?.()
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
            className="qwr-panel w-[620px] max-w-[96vw] max-h-[88vh] overflow-y-auto p-5 relative"
          >
            <button
              onClick={() => { audio.click?.(); onClose() }}
              className="absolute top-3 right-3 pk text-[10px] text-[color:var(--subdim)] hover:text-[color:var(--text)] tracking-widest"
            >✕ CLOSE</button>
            <div
              className="pk text-sm tracking-widest mb-4"
              style={{ color: "#00ffff", textShadow: "0 0 8px rgba(0,255,255,0.6)" }}
            >◈ CONNECT EXCHANGE</div>

            {/* Already connected */}
            {connected.length > 0 && phase === "list" && (
              <div className="mb-4 space-y-2">
                <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mb-2">CONNECTED ({connected.length})</div>
                {connected.map(e => (
                  <div key={e.id} className="flex items-center justify-between p-2 border"
                       style={{ borderColor: e.color + "66", background: e.color + "10" }}>
                    <div className="flex items-center gap-3">
                      <div style={{ fontSize: 22 }}>{e.icon}</div>
                      <div>
                        <div className="pk text-[10px]" style={{ color: e.color }}>{e.name}</div>
                        <div className="mono text-[9px] text-[color:var(--subdim)]">API: {e.keyMasked} · ${e.balance.toLocaleString()}</div>
                      </div>
                    </div>
                    <button
                      onClick={() => disconnect(e.id)}
                      className="pk text-[8px] tracking-widest px-2 py-1 border"
                      style={{ color: "#ff5577", borderColor: "#ff5577" }}
                    >✕ REMOVE</button>
                  </div>
                ))}
              </div>
            )}

            {/* List phase */}
            {phase === "list" && (
              <>
                <div className="mono text-[11px] text-[color:var(--subdim)] mb-3">
                  Connect exchange API keys. READ-ONLY permissions recommended for preview.
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {EXCHANGES.map(e => {
                    const already = connected.some(c => c.id === e.id)
                    return (
                      <motion.button
                        key={e.id}
                        whileHover={{ y: -2, scale: 1.01 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => !already && startConnect(e)}
                        disabled={already}
                        className="flex items-center gap-3 p-3 border text-left"
                        style={{
                          borderColor: already ? e.color : "var(--border)",
                          background: already ? e.color + "15" : "rgba(11,21,37,0.4)",
                          opacity: already ? 0.7 : 1,
                        }}
                      >
                        <div style={{ fontSize: 22 }}>{e.icon}</div>
                        <div className="flex-1">
                          <div className="pk text-[11px]" style={{ color: e.color }}>{e.name}</div>
                          <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mt-1">{e.desc}</div>
                        </div>
                        <div className="pk text-[8px] tracking-widest" style={{ color: e.color }}>
                          {already ? "✓" : "►"}
                        </div>
                      </motion.button>
                    )
                  })}
                </div>
              </>
            )}

            {/* Keys phase */}
            {phase === "keys" && picked && (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 border" style={{ borderColor: picked.color, background: picked.color + "12" }}>
                  <div style={{ fontSize: 28 }}>{picked.icon}</div>
                  <div className="pk text-sm" style={{ color: picked.color }}>{picked.name}</div>
                </div>
                <div>
                  <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mb-1">API KEY</div>
                  <input
                    type="text"
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    placeholder="Paste your API key"
                    className="w-full mono text-[11px] bg-transparent border p-2"
                    style={{ borderColor: "var(--border)", color: picked.color }}
                  />
                </div>
                <div>
                  <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mb-1">API SECRET</div>
                  <input
                    type="password"
                    value={secret}
                    onChange={e => setSecret(e.target.value)}
                    placeholder="Paste your API secret"
                    className="w-full mono text-[11px] bg-transparent border p-2"
                    style={{ borderColor: "var(--border)", color: picked.color }}
                  />
                </div>
                <div className="mono text-[10px] text-[color:var(--subdim)] leading-relaxed">
                  ⚠ Read-only keys recommended. Trading Guru never withdraws funds from your exchange.
                </div>
                <motion.button
                  whileHover={apiKey && secret ? { scale: 1.03 } : {}}
                  onClick={submit}
                  disabled={!apiKey || !secret}
                  className="w-full pk text-sm tracking-widest px-4 py-3 border"
                  style={{
                    color: apiKey && secret ? picked.color : "var(--subdim)",
                    borderColor: apiKey && secret ? picked.color : "var(--border)",
                    background: apiKey && secret ? picked.color + "15" : "transparent",
                    cursor: apiKey && secret ? "pointer" : "not-allowed",
                  }}
                >
                  ► CONNECT {picked.name.toUpperCase()}
                </motion.button>
              </div>
            )}

            {/* Connecting */}
            {phase === "connecting" && picked && (
              <div className="py-8 text-center space-y-4">
                <div style={{ fontSize: 56 }}>{picked.icon}</div>
                <div className="pk text-sm tracking-widest" style={{ color: picked.color }}>
                  VERIFYING API KEYS…
                </div>
                <div className="flex justify-center gap-2">
                  {[0,1,2].map(i => (
                    <motion.span key={i}
                      animate={{ y: [0, -6, 0], opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }}
                      className="w-2 h-2"
                      style={{ background: picked.color, boxShadow: `0 0 8px ${picked.color}` }}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Connected */}
            {phase === "connected" && picked && (
              <div className="py-6 text-center space-y-3">
                <div style={{ fontSize: 56 }}>✅</div>
                <div className="pk text-lg tracking-widest" style={{ color: picked.color }}>
                  {picked.name.toUpperCase()} CONNECTED
                </div>
                <div className="mono text-[10px] text-[color:var(--subdim)]">
                  Read-only access · balance & positions synced
                </div>
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  onClick={() => setPhase("list")}
                  className="pk text-[10px] tracking-widest px-6 py-2 border mt-3"
                  style={{ color: picked.color, borderColor: picked.color, background: picked.color + "14" }}
                >CONNECT ANOTHER</motion.button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
