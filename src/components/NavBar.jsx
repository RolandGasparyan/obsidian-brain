import { useEffect, useState } from "react"
import { Link, useLocation } from "react-router-dom"
import { motion } from "framer-motion"
import { audio } from "../ui/audio_engine.js"
import WalletConnectModal, { getConnectedWallet } from "./WalletConnectModal.jsx"
import ExchangeConnectModal, { getExchanges } from "./ExchangeConnectModal.jsx"

const LINKS = [
  { to: "/",             label: "HOME",         color: "#00ff41", icon: "◆" },
  { to: "/dashboard",    label: "ACCOUNT",      color: "#00ffff", icon: "►" },
  { to: "/arena",        label: "ARENA",        color: "#ff5577", icon: "◢" },
  { to: "/war-room",     label: "WAR ROOM",     color: "#ff9b3d", icon: "◈" },
  { to: "/championship", label: "CHAMPIONSHIP", color: "#ffff00", icon: "★" },
]

export default function NavBar() {
  const { pathname } = useLocation()
  const [wallet, setWallet] = useState(() => getConnectedWallet())
  const [walletOpen, setWalletOpen] = useState(false)
  const [exchanges, setExchanges] = useState(() => getExchanges())
  const [exOpen, setExOpen] = useState(false)

  useEffect(() => {
    const onWallet = (e) => setWallet(e.detail)
    const onEx = (e) => setExchanges(e.detail)
    window.addEventListener("qwr:wallet", onWallet)
    window.addEventListener("qwr:exchanges", onEx)
    return () => {
      window.removeEventListener("qwr:wallet", onWallet)
      window.removeEventListener("qwr:exchanges", onEx)
    }
  }, [])

  return (
    <>
      <nav
        className="fixed top-0 inset-x-0 z-[90] qwr-panel px-4 py-2 flex items-center justify-between gap-3"
        style={{
          background: "linear-gradient(180deg, rgba(11,21,37,0.85) 0%, rgba(8,15,30,0.7) 100%)",
          backdropFilter: "blur(10px) saturate(1.15)",
          WebkitBackdropFilter: "blur(10px) saturate(1.15)",
        }}
      >
        {/* Brand */}
        <Link to="/" onClick={() => audio.click?.()}>
          <motion.div
            whileHover={{ scale: 1.03 }}
            className="pk text-[10px] tracking-widest"
            style={{ color: "#00ff41", textShadow: "0 0 8px rgba(0,255,65,0.6)" }}
          >
            ► TRADING GURU
          </motion.div>
        </Link>

        {/* Links */}
        <div className="flex items-center gap-1 md:gap-4 flex-wrap">
          {LINKS.map((l) => {
            const active = pathname === l.to
            return (
              <Link key={l.to} to={l.to} onClick={() => audio.click?.()}>
                <motion.div
                  whileHover={{ y: -2 }}
                  whileTap={{ scale: 0.95 }}
                  className="pk text-[9px] md:text-[10px] tracking-widest px-2 py-1 border transition-colors"
                  style={{
                    color: active ? l.color : "var(--subdim)",
                    borderColor: active ? l.color : "transparent",
                    background: active ? `${l.color}14` : "transparent",
                    boxShadow: active ? `0 0 10px ${l.color}44` : "none",
                    textShadow: active ? `0 0 6px ${l.color}80` : "none",
                  }}
                >
                  {l.icon} {l.label}
                </motion.div>
              </Link>
            )
          })}
        </div>

        {/* Wallet Connect — also surfaces Exchange connect via tabs */}
        <motion.button
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
          onClick={() => { audio.click?.(); setWalletOpen(true) }}
          className="pk text-[9px] md:text-[10px] tracking-widest px-3 py-1.5 border flex items-center gap-2"
          style={{
            color: wallet ? wallet.color : "#ffff00",
            borderColor: wallet ? wallet.color : "#ffff00",
            background: wallet ? wallet.color + "14" : "rgba(255,255,0,0.08)",
            boxShadow: wallet
              ? `0 0 10px ${wallet.color}55`
              : "0 0 10px rgba(255,255,0,0.3)",
          }}
        >
          {wallet ? (
            <>
              <span style={{ fontSize: 14 }}>{wallet.icon}</span>
              <span className="hidden md:inline">
                {wallet.address.slice(0, 6)}…{wallet.address.slice(-4)}
              </span>
              <span className="md:hidden">{wallet.name.slice(0, 6)}</span>
              {exchanges.length > 0 && (
                <span className="pk text-[8px] px-1 ml-1 border" style={{ color: "#00ffff", borderColor: "#00ffff" }}>
                  +{exchanges.length}
                </span>
              )}
            </>
          ) : (
            <>
              <span>◆</span> CONNECT
            </>
          )}
        </motion.button>
      </nav>

      <WalletConnectModal open={walletOpen} onClose={() => setWalletOpen(false)} />
    </>
  )
}
