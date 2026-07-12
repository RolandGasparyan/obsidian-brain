import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { audio } from "../ui/audio_engine.js"
import ExchangeConnectModal, { getExchanges } from "./ExchangeConnectModal.jsx"

const WALLETS = [
  { id: "metamask",     name: "MetaMask",        color: "#f6851b", icon: "🦊", desc: "Browser · popular" },
  { id: "walletconnect",name: "WalletConnect",   color: "#3b99fc", icon: "◎",  desc: "Mobile · QR code" },
  { id: "coinbase",     name: "Coinbase Wallet", color: "#0052ff", icon: "◆",  desc: "Coinbase · web/mobile" },
  { id: "phantom",      name: "Phantom",         color: "#ab9ff2", icon: "👻", desc: "Solana · multi-chain" },
  { id: "trust",        name: "Trust Wallet",    color: "#3375bb", icon: "🛡",  desc: "Mobile · multi-chain" },
  { id: "rabby",        name: "Rabby",           color: "#ff5b4f", icon: "🐰", desc: "Browser · DeFi" },
  { id: "ledger",       name: "Ledger",          color: "#e6e6e6", icon: "⬡",  desc: "Hardware · secure" },
  { id: "binance",      name: "Binance Wallet",  color: "#f3ba2f", icon: "◈",  desc: "BNB · web/mobile" },
]

const STORAGE_KEY = "qwr.wallet.v1"

export function getConnectedWallet() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null") } catch { return null }
}
export function setConnectedWallet(w) {
  if (w) localStorage.setItem(STORAGE_KEY, JSON.stringify(w))
  else   localStorage.removeItem(STORAGE_KEY)
  window.dispatchEvent(new CustomEvent("qwr:wallet", { detail: w }))
}

function mockAddress() {
  const chars = "0123456789abcdef"
  let a = "0x"
  for (let i = 0; i < 40; i++) a += chars[Math.floor(Math.random() * 16)]
  return a
}

export default function WalletConnectModal({ open, onClose }) {
  const [phase, setPhase] = useState("select")   // select | connecting | connected | error
  const [picked, setPicked] = useState(null)
  const [wallet, setWallet] = useState(() => getConnectedWallet())
  const [exchanges, setExchanges] = useState(() => getExchanges())
  const [exOpen, setExOpen] = useState(false)

  useEffect(() => {
    if (!open) { setPhase("select"); setPicked(null) }
  }, [open])

  useEffect(() => {
    const onEx = (e) => setExchanges(e.detail)
    window.addEventListener("qwr:exchanges", onEx)
    return () => window.removeEventListener("qwr:exchanges", onEx)
  }, [])

  const connect = (w) => {
    setPicked(w)
    setPhase("connecting")
    audio.click?.()
    // Simulate connection flow — 1.5s connecting, 90% success rate
    setTimeout(() => {
      if (Math.random() > 0.08) {
        const connected = {
          wallet: w.id,
          name: w.name,
          color: w.color,
          icon: w.icon,
          address: mockAddress(),
          balance: +(Math.random() * 10000 + 100).toFixed(2),
          connectedAt: Date.now(),
        }
        setConnectedWallet(connected)
        setWallet(connected)
        setPhase("connected")
        audio.triumph?.()
      } else {
        setPhase("error")
      }
    }, 1500)
  }

  const disconnect = () => {
    setConnectedWallet(null)
    setWallet(null)
    setPhase("select")
    audio.click?.()
  }

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
            className="qwr-panel w-[560px] max-w-[96vw] max-h-[88vh] overflow-y-auto p-5 relative"
          >
            {/* Close */}
            <button
              onClick={() => { audio.click?.(); onClose() }}
              className="absolute top-3 right-3 pk text-[10px] text-[color:var(--subdim)] hover:text-[color:var(--text)] tracking-widest"
            >
              ✕ CLOSE
            </button>

            {/* Header */}
            <div
              className="pk text-sm tracking-widest mb-4"
              style={{ color: "#00ff41", textShadow: "0 0 8px rgba(0,255,65,0.6)" }}
            >
              ◆ CONNECT WALLET
            </div>

            {/* CONNECTED state */}
            {wallet && phase !== "select" && phase !== "connecting" ? null : wallet && (
              <div className="mb-4 p-3 border" style={{
                borderColor: wallet.color + "88",
                background: wallet.color + "12",
              }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div style={{ fontSize: 28 }}>{wallet.icon}</div>
                    <div>
                      <div className="pk text-[11px]" style={{ color: wallet.color }}>
                        {wallet.name}
                      </div>
                      <div className="mono text-[10px] text-[color:var(--text)] mt-1">
                        {wallet.address.slice(0, 10)}…{wallet.address.slice(-6)}
                      </div>
                      <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mt-1">
                        BALANCE ${wallet.balance.toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.04 }}
                    onClick={disconnect}
                    className="pk text-[9px] tracking-widest px-3 py-2 border"
                    style={{
                      color: "#ff5577",
                      borderColor: "#ff5577",
                      background: "rgba(255,85,119,0.08)",
                    }}
                  >
                    DISCONNECT
                  </motion.button>
                </div>
              </div>
            )}

            {/* SELECT phase */}
            {phase === "select" && (
              <>
                <div className="mono text-[11px] text-[color:var(--subdim)] mb-3">
                  Pick a wallet to connect. Trading funds deposit directly; no custody by Trading Guru.
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {WALLETS.map(w => (
                    <motion.button
                      key={w.id}
                      whileHover={{ y: -2, scale: 1.01 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => connect(w)}
                      className="flex items-center gap-3 p-3 border text-left"
                      style={{
                        borderColor: "var(--border)",
                        background: "rgba(11,21,37,0.4)",
                      }}
                    >
                      <div style={{ fontSize: 26 }}>{w.icon}</div>
                      <div className="flex-1">
                        <div className="pk text-[11px]" style={{ color: w.color }}>
                          {w.name}
                        </div>
                        <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mt-1">
                          {w.desc}
                        </div>
                      </div>
                      <div
                        className="pk text-[8px] tracking-widest"
                        style={{ color: w.color }}
                      >
                        ►
                      </div>
                    </motion.button>
                  ))}
                </div>
                <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mt-4 text-center">
                  ◆ PREVIEW MODE · WALLETS ARE SIMULATED · NO REAL SIGNATURES
                </div>

                {/* Exchange connect section */}
                <div className="mt-5 pt-4 border-t border-[color:var(--border)]">
                  <div className="flex items-center justify-between mb-3">
                    <div
                      className="pk text-[10px] tracking-widest"
                      style={{ color: "#00ffff", textShadow: "0 0 6px rgba(0,255,255,0.5)" }}
                    >
                      ◈ CONNECT EXCHANGE
                      {exchanges.length > 0 && (
                        <span className="ml-2 pk text-[8px]" style={{ color: "#00ff41" }}>
                          · {exchanges.length} LINKED
                        </span>
                      )}
                    </div>
                    <motion.button
                      whileHover={{ scale: 1.04 }}
                      whileTap={{ scale: 0.96 }}
                      onClick={() => { audio.click?.(); setExOpen(true) }}
                      className="pk text-[9px] tracking-widest px-3 py-1.5 border"
                      style={{
                        color: "#00ffff",
                        borderColor: "#00ffff",
                        background: "rgba(0,255,255,0.08)",
                        boxShadow: "0 0 10px rgba(0,255,255,0.3)",
                      }}
                    >
                      {exchanges.length > 0 ? "MANAGE" : "CONNECT"} ►
                    </motion.button>
                  </div>
                  {exchanges.length > 0 && (
                    <div className="space-y-1.5">
                      {exchanges.map(e => (
                        <div
                          key={e.id}
                          className="flex items-center gap-2 p-2 border"
                          style={{ borderColor: e.color + "44", background: e.color + "08" }}
                        >
                          <span style={{ fontSize: 16 }}>{e.icon}</span>
                          <div className="flex-1">
                            <div className="pk text-[9px]" style={{ color: e.color }}>{e.name}</div>
                            <div className="mono text-[8px] text-[color:var(--subdim)]">
                              API: {e.keyMasked}
                            </div>
                          </div>
                          <div className="pk text-[9px]" style={{ color: "#00ff41" }}>
                            ${e.balance.toLocaleString()}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mt-2 text-center">
                    LINK BINANCE · COINBASE · KRAKEN · BYBIT · KUCOIN · + MORE
                  </div>
                </div>
              </>
            )}

            {/* CONNECTING phase */}
            {phase === "connecting" && picked && (
              <div className="py-8 text-center space-y-4">
                <div style={{ fontSize: 56 }}>{picked.icon}</div>
                <div
                  className="pk text-sm tracking-widest"
                  style={{ color: picked.color, textShadow: `0 0 10px ${picked.color}aa` }}
                >
                  CONNECTING TO {picked.name.toUpperCase()}…
                </div>
                <div className="flex justify-center gap-2">
                  {[0, 1, 2].map(i => (
                    <motion.span
                      key={i}
                      animate={{ y: [0, -6, 0], opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }}
                      className="w-2 h-2"
                      style={{ background: picked.color, boxShadow: `0 0 8px ${picked.color}` }}
                    />
                  ))}
                </div>
                <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)]">
                  APPROVE THE CONNECTION IN YOUR WALLET
                </div>
              </div>
            )}

            {/* CONNECTED phase (final confirmation) */}
            {phase === "connected" && wallet && (
              <div className="py-6 text-center space-y-3">
                <div style={{ fontSize: 56 }}>✅</div>
                <div
                  className="pk text-lg tracking-widest"
                  style={{ color: "#00ff41", textShadow: "0 0 14px rgba(0,255,65,0.7)" }}
                >
                  CONNECTED
                </div>
                <div className="mono text-[11px] text-[color:var(--text)]">
                  {wallet.name}
                </div>
                <div className="mono text-[10px] text-[color:var(--subdim)]">
                  {wallet.address.slice(0, 12)}…{wallet.address.slice(-8)}
                </div>
                <div className="pk text-[9px] tracking-widest mt-2" style={{ color: "#ffff00" }}>
                  BALANCE: ${wallet.balance.toLocaleString()} USDT
                </div>
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  onClick={() => { audio.click?.(); onClose() }}
                  className="pk text-[10px] tracking-widest px-6 py-2 border mt-3"
                  style={{
                    color: "#00ff41",
                    borderColor: "#00ff41",
                    background: "rgba(0,255,65,0.1)",
                  }}
                >
                  CONTINUE ►
                </motion.button>
              </div>
            )}

            {/* ERROR phase */}
            {phase === "error" && picked && (
              <div className="py-6 text-center space-y-3">
                <div style={{ fontSize: 56 }}>⚠</div>
                <div
                  className="pk text-sm tracking-widest"
                  style={{ color: "#ff5577", textShadow: "0 0 10px rgba(255,85,119,0.6)" }}
                >
                  CONNECTION FAILED
                </div>
                <div className="mono text-[11px] text-[color:var(--subdim)]">
                  Unable to connect to {picked.name}. Check wallet is unlocked and try again.
                </div>
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  onClick={() => setPhase("select")}
                  className="pk text-[10px] tracking-widest px-6 py-2 border mt-3"
                  style={{
                    color: "#00ffff",
                    borderColor: "#00ffff",
                    background: "rgba(0,255,255,0.1)",
                  }}
                >
                  ◄ TRY ANOTHER WALLET
                </motion.button>
              </div>
            )}
          </motion.div>

          {/* Nested exchange modal (rendered inside wallet modal) */}
          <ExchangeConnectModal open={exOpen} onClose={() => setExOpen(false)} />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
