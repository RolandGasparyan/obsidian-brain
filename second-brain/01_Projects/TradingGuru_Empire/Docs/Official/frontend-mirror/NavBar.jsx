import { useEffect, useState, useMemo } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { motion } from "framer-motion"
import { audio } from "../ui/audio_engine.js"
import WalletConnectModal, { getConnectedWallet } from "./WalletConnectModal.jsx"
import ExchangeConnectModal, { getExchanges } from "./ExchangeConnectModal.jsx"
import LoginModal, { getSession, clearSession } from "./LoginModal.jsx"
import TradingGuruLogo from "./TradingGuruLogo.jsx"  // restored 2026-05-13, animated SVG version
// Phase A 2026-05-11: hamburger drawer for mobile (replaces overflow-x-auto scroll bar)
import MobileNav, { HamburgerButton } from "./MobileNav.jsx"

const LINKS = [
  { to: "/",             label: "HOME",         color: "var(--accent-green)", icon: "◆", gated: false },
  { to: "/dashboard",    label: "ACCOUNT",      color: "var(--accent-cyan)", icon: "►", gated: true  },
  { to: "/arena",        label: "ARENA",        color: "var(--accent-pink)", icon: "◢", gated: false },
  { to: "/war-room",     label: "WAR ROOM",     color: "#ff9b3d", icon: "◈", gated: true  },
  { to: "/championship", label: "CHAMPIONSHIP", color: "var(--accent-yellow)", icon: "★", gated: false },
  { to: "/predictions",  label: "PREDICT",      color: "var(--accent-purple)", icon: "▲", gated: false },
  { to: "/control",      label: "CONTROL",      color: "var(--accent-cyan)", icon: "◇", gated: true  },
]

// ── Floating sparkle particles inside the nav ─────────────────
function NavSparkles({ count = 14 }) {
  const sparks = useMemo(() => Array.from({ length: count }, (_, i) => ({
    id: i,
    left: 5 + Math.random() * 90,           // %
    top:  8 + Math.random() * 84,           // %
    size: 2 + Math.random() * 3,
    color: ["var(--accent-green)","var(--accent-cyan)","var(--accent-yellow)","#ff9b3d","var(--accent-pink)","var(--accent-purple)"][i % 6],
    dur: 2.4 + Math.random() * 2.6,
    delay: Math.random() * 2,
  })), [count])
  return (
    <div aria-hidden style={{
      position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden",
    }}>
      {sparks.map(s => (
        <motion.span
          key={s.id}
          animate={{
            opacity: [0, 0.85, 0],
            scale:  [0.4, 1.3, 0.4],
            y: [0, -8, 0],
          }}
          transition={{
            duration: s.dur, repeat: Infinity, delay: s.delay, ease: "easeInOut",
          }}
          style={{
            position: "absolute",
            left: `${s.left}%`, top: `${s.top}%`,
            width: s.size, height: s.size,
            borderRadius: "50%",
            background: s.color,
            boxShadow: `0 0 ${s.size * 3}px ${s.color}`,
          }}
        />
      ))}
    </div>
  )
}

// ── Per-link colored aura with hover bloom ────────────────────
/**
 * NavLink — neon redesign 2026-05-11 per EXECUTE_NEON_CENTER_NAVLINKS.
 * Continuous color-tinted breathing + shimmer sweep + active sparks.
 */
function NavLink({ l, active, locked, onClick }) {
  // 2026-05-12 — all nav button borders unified to neon green with slow breathing
  // animation per operator request. Per-link colors (l.color) preserved for text,
  // glow, active markers, hover bloom — so each page is still color-coded.
  const GREEN = "#00ff41" // var(--accent-green) literal for animate keyframes
  return (
    <Link to={l.to} onClick={onClick} className="relative">
      <motion.div
        whileHover={{ y: -4, scale: 1.09 }}
        whileTap={{ scale: 0.94 }}
        animate={{
          // Slow breathing border opacity — green throughout, alpha cycles
          borderColor: active
            ? [
                `rgba(0,255,65,0.75)`,
                `rgba(0,255,65,1)`,
                `rgba(0,255,65,0.75)`,
              ]
            : [
                `rgba(0,255,65,0.40)`,
                `rgba(0,255,65,0.85)`,
                `rgba(0,255,65,0.40)`,
              ],
          // Box shadow stays per-link color so each page still has identity glow
          boxShadow: active
            ? [
                `0 0 22px ${l.color}88, 0 0 38px ${l.color}44, inset 0 0 14px ${l.color}33`,
                `0 0 32px ${l.color}cc, 0 0 56px ${l.color}66, inset 0 0 22px ${l.color}55`,
                `0 0 22px ${l.color}88, 0 0 38px ${l.color}44, inset 0 0 14px ${l.color}33`,
              ]
            : [
                `0 0 6px ${l.color}22, inset 0 0 4px ${l.color}11`,
                `0 0 14px ${l.color}55, inset 0 0 8px ${l.color}22`,
                `0 0 6px ${l.color}22, inset 0 0 4px ${l.color}11`,
              ],
        }}
        transition={{
          // SLOW breathing — 3.5s active, 4.2s inactive (was 1.6 / 2.8)
          borderColor: { duration: active ? 3.5 : 4.2, repeat: Infinity, ease: "easeInOut" },
          boxShadow:   { duration: active ? 3.5 : 4.2, repeat: Infinity, ease: "easeInOut" },
        }}
        className="relative pk text-[10px] lg:text-[11px] tracking-widest px-4 py-2.5 border-2 overflow-hidden"
        style={{
          color: active ? l.color : (locked ? "rgba(180,200,220,0.55)" : `${l.color}dd`),
          // Initial green border before animation kicks in (prevents flash)
          borderColor: GREEN,
          background: active
            ? `linear-gradient(135deg, ${l.color}33, ${l.color}0a, ${l.color}1f)`
            : `linear-gradient(135deg, rgba(8,15,30,0.7), rgba(11,21,37,0.4))`,
          textShadow: active
            ? `0 0 10px ${l.color}, 0 0 20px ${l.color}88`
            : `0 0 6px ${l.color}77`,
          borderRadius: 4,
        }}
      >
        {/* Continuous neon shimmer sweep — color-tinted */}
        <motion.span
          aria-hidden
          animate={{ x: ["-160%", "220%"] }}
          transition={{ duration: active ? 2.5 : 4.5, repeat: Infinity, ease: "linear" }}
          style={{
            position: "absolute", inset: 0,
            background: `linear-gradient(110deg, transparent 35%, ${l.color}55 50%, transparent 65%)`,
            pointerEvents: "none",
            mixBlendMode: "screen",
          }}
        />

        {/* hover bloom — radial color flash */}
        <motion.span
          aria-hidden
          className="absolute inset-0 pointer-events-none"
          initial={{ opacity: 0 }}
          whileHover={{ opacity: 1 }}
          transition={{ duration: 0.25 }}
          style={{
            background: `radial-gradient(circle at 50% 100%, ${l.color}88, transparent 75%)`,
          }}
        />

        {/* spinning icon on hover */}
        <motion.span
          whileHover={{ rotate: 360, scale: 1.35 }}
          transition={{ duration: 0.55 }}
          style={{ display: "inline-block", marginRight: 6, position: "relative", zIndex: 2 }}
        >
          {l.icon}
        </motion.span>
        <span style={{ position: "relative", zIndex: 2 }}>{l.label}</span>
        {locked && (
          <motion.span
            animate={{ opacity: [0.55, 1, 0.55], rotate: [0, 8, -8, 0] }}
            transition={{ duration: 1.6, repeat: Infinity }}
            style={{ marginLeft: 6, fontSize: 9, opacity: 0.9, position: "relative", zIndex: 2 }}
          >
            🔒
          </motion.span>
        )}

        {/* active marker — pulsing dot + underline + corner sparks */}
        {active && (
          <>
            <motion.span
              aria-hidden
              animate={{
                scale: [0.7, 1.5, 0.7],
                opacity: [0.6, 1, 0.6],
              }}
              transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
              style={{
                position: "absolute", top: -4, left: "50%",
                transform: "translateX(-50%)",
                width: 5, height: 5, borderRadius: "50%",
                background: l.color,
                boxShadow: `0 0 10px ${l.color}, 0 0 18px ${l.color}cc`,
              }}
            />
            <motion.div
              layoutId="nav-underline"
              className="absolute left-2 right-2 -bottom-[3px] h-[2px]"
              style={{
                background: l.color,
                boxShadow: `0 0 10px ${l.color}, 0 0 20px ${l.color}aa`,
              }}
            />
            <motion.span
              aria-hidden
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.8, repeat: Infinity, delay: 0.2 }}
              style={{
                position: "absolute", top: 2, left: 2,
                width: 4, height: 4, borderTop: `1px solid ${l.color}`,
                borderLeft: `1px solid ${l.color}`,
                boxShadow: `0 0 6px ${l.color}`,
              }}
            />
            <motion.span
              aria-hidden
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.8, repeat: Infinity, delay: 1.1 }}
              style={{
                position: "absolute", bottom: 2, right: 2,
                width: 4, height: 4, borderBottom: `1px solid ${l.color}`,
                borderRight: `1px solid ${l.color}`,
                boxShadow: `0 0 6px ${l.color}`,
              }}
            />
          </>
        )}
      </motion.div>
    </Link>
  )
}

export default function NavBar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [wallet, setWallet] = useState(() => getConnectedWallet())
  const [walletOpen, setWalletOpen] = useState(false)
  const [exchanges, setExchanges] = useState(() => getExchanges())
  const [loginOpen, setLoginOpen] = useState(false)
  const [session, setSession] = useState(() => getSession())
  // Phase A 2026-05-11: hamburger drawer state for mobile
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const onWallet = (e) => setWallet(e.detail)
    const onEx = (e) => setExchanges(e.detail)
    const onSession = (e) => setSession(e.detail)
    window.addEventListener("qwr:wallet", onWallet)
    window.addEventListener("qwr:exchanges", onEx)
    window.addEventListener("qwr:session", onSession)
    return () => {
      window.removeEventListener("qwr:wallet", onWallet)
      window.removeEventListener("qwr:exchanges", onEx)
      window.removeEventListener("qwr:session", onSession)
    }
  }, [])

  useEffect(() => {
    const t = setInterval(() => setTick(v => v + 1), 220)
    return () => clearInterval(t)
  }, [])

  const handleLink = (l, e) => {
    audio.click?.()
    if (l.gated && !session) {
      e.preventDefault()
      setLoginOpen(true)
    }
  }

  const handleLogout = () => {
    audio.click?.()
    clearSession()
    if (pathname.startsWith("/dashboard") || pathname.startsWith("/war-room")) {
      navigate("/")
    }
  }

  // brand color cycle through arena palette
  const brandPalette = ["var(--accent-green)","var(--accent-cyan)","var(--accent-yellow)","#ff9b3d","var(--accent-pink)","var(--accent-purple)"]
  const brandColor = brandPalette[Math.floor(tick / 6) % brandPalette.length]

  return (
    <>
      <nav
        className="fixed top-0 inset-x-0 z-[90] px-4 md:px-8 py-3 md:py-4 flex items-center justify-between gap-4"
        style={{
          background:
            "linear-gradient(180deg, rgba(11,21,37,0.94) 0%, rgba(8,15,30,0.78) 70%, rgba(8,15,30,0) 100%)",
          backdropFilter: "blur(16px) saturate(1.3)",
          WebkitBackdropFilter: "blur(16px) saturate(1.3)",
          borderBottom: "1px solid rgba(0,255,65,0.18)",
          boxShadow: "0 8px 32px -10px rgba(0,255,65,0.3), 0 6px 28px -16px rgba(204,68,255,0.25)",
        }}
      >
        {/* ── floating sparkles backdrop ── */}
        <NavSparkles count={14}/>

        {/* ── animated rainbow strip (bottom) ── */}
        <motion.div
          aria-hidden
          className="absolute left-0 right-0 bottom-0 h-px pointer-events-none"
          animate={{ backgroundPosition: ["0% 50%", "200% 50%"] }}
          transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
          style={{
            background:
              "linear-gradient(90deg, #00ff41 0%, #00ffff 20%, #ffff00 40%, #ff9b3d 60%, #ff5577 80%, #cc44ff 100%, #00ff41 120%)",
            backgroundSize: "200% 100%",
            opacity: 0.85,
            filter: "blur(0.4px)",
            height: 2,
          }}
        />

        {/* ── ambient gradient blobs (subtle) ── */}
        <motion.div
          aria-hidden
          className="absolute pointer-events-none"
          animate={{ x: ["-20%", "120%"] }}
          transition={{ duration: 14, repeat: Infinity, ease: "linear" }}
          style={{
            top: 0, left: 0, width: 240, height: "100%",
            background: "radial-gradient(circle at 50% 50%, rgba(0,255,255,0.12), transparent 60%)",
          }}
        />
        <motion.div
          aria-hidden
          className="absolute pointer-events-none"
          animate={{ x: ["120%", "-20%"] }}
          transition={{ duration: 17, repeat: Infinity, ease: "linear" }}
          style={{
            top: 0, right: 0, width: 240, height: "100%",
            background: "radial-gradient(circle at 50% 50%, rgba(204,68,255,0.12), transparent 60%)",
          }}
        />

        {/* BRAND block — restored 2026-05-13 with animated SVG TradingGuruLogo.
            Continuous 20s rotation + 4s glow pulse + hover scale + click → home. */}
        <Link to='/' onClick={() => audio.click?.()} className='relative z-10 flex items-center gap-2 mr-3 ml-1 pointer-events-auto' aria-label='Trading Guru Home'>
          <TradingGuruLogo size={38} />
          <span className='pk text-[10px] tracking-widest hidden md:inline'
                style={{ color: brandColor, textShadow: `0 0 8px ${brandColor}` }}>
            TRADING<br/>GURU
          </span>
        </Link>

        {/* Left flex spacer — centers the desktop nav links geometrically.
            Added 2026-05-11 per EXECUTE_NEON_CENTER_NAVLINKS. */}
        <div className="hidden md:flex flex-1 min-w-0 relative z-10" />

        {/* ── DESKTOP LINKS — centered ── */}
        <div className="hidden md:flex items-center gap-2 lg:gap-3 relative z-10 flex-shrink-0">
          {LINKS.map((l) => {
            const active = pathname === l.to
            const locked = l.gated && !session
            return <NavLink key={l.to} l={l} active={active} locked={locked}
                            onClick={(e) => handleLink(l, e)}/>
          })}
        </div>

        {/* Right flex spacer — symmetric balance for the centered links.
            Wallet pill / login session live in their own block after the spacer. */}
        <div className="hidden md:flex flex-1 min-w-0 relative z-10" />

        {/* ── MOBILE NAV TRIGGER (Phase A 2026-05-11) ──
            Replaces overflow-x-auto horizontal scroll with hamburger drawer.
            Drawer itself rendered at bottom of NavBar (after </nav>). */}
        <div className="flex md:hidden items-center gap-2 relative z-10">
          <HamburgerButton open={mobileNavOpen} onClick={() => { audio.click?.(); setMobileNavOpen(o => !o) }} />
        </div>

        {/* ── LOG IN / SESSION ── */}
        <div className="relative z-10 flex items-center gap-2">
          {session ? (
            <div className="hidden md:flex items-center gap-2">
              <div className="pk text-[10px] tracking-widest px-3 py-2 border flex items-center gap-2"
                   style={{
                     color: "var(--accent-green)",
                     borderColor: "rgba(0,255,65,0.5)",
                     background: "linear-gradient(135deg, rgba(0,255,65,0.16), rgba(0,255,65,0.04))",
                     boxShadow: "0 0 12px rgba(0,255,65,0.35), inset 0 0 8px rgba(0,255,65,0.14)",
                   }}>
                <motion.span
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 1.4, repeat: Infinity }}
                  style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: "var(--accent-green)", boxShadow: "0 0 8px #00ff41",
                    display: "inline-block",
                  }}/>
                <span className="hidden lg:inline">{session.name?.toUpperCase().slice(0, 12)}</span>
                <span className="lg:hidden">●</span>
              </div>
              <motion.button
                whileHover={{ scale: 1.05, rotate: 90 }}
                whileTap={{ scale: 0.94 }}
                onClick={handleLogout}
                className="pk text-[9px] tracking-widest px-2 py-2 border"
                style={{
                  color: "var(--subdim)", borderColor: "var(--border)",
                  background: "rgba(8,15,30,0.6)",
                }}
              >
                ✕
              </motion.button>
            </div>
          ) : (
            /* P1 redesign 2026-05-11: LOG IN/SIGN UP button removed per operator.
               Login still triggered via gated nav links (handleLink → setLoginOpen).
               Wallet status now standalone, animated holographic pill. */
            /* WIRE_WALLET_CONNECT_TRIGGER 2026-05-12:
               Both pills are now clickable buttons that open WalletConnectModal.
               Restores wallet/exchange connect access lost when standalone
               CONNECT button was removed in P1. */
            wallet ? (
              <motion.button
                whileHover={{ scale: 1.05, y: -1 }}
                whileTap={{ scale: 0.96 }}
                onClick={() => { audio.click?.(); setWalletOpen(true) }}
                aria-label="Manage connected wallet"
                className="pk text-[9px] md:text-[10px] tracking-widest px-3 py-1.5 border-2 min-h-touch flex items-center gap-1.5 flex-shrink-0 relative overflow-hidden"
                style={{
                  color: wallet.color,
                  borderColor: wallet.color,
                  background: `linear-gradient(135deg, ${wallet.color}22, ${wallet.color}06)`,
                  boxShadow: `0 0 10px ${wallet.color}55, inset 0 0 6px ${wallet.color}18`,
                  borderRadius: 4,
                  cursor: "pointer",
                }}
                title={`${wallet.name} ${wallet.address.slice(0, 6)}…${wallet.address.slice(-4)} · click to manage`}
              >
                {/* holographic sweep */}
                <motion.span
                  aria-hidden
                  animate={{ x: ["-150%", "200%"] }}
                  transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
                  style={{
                    position: "absolute", inset: 0,
                    background: `linear-gradient(90deg, transparent, ${wallet.color}33, transparent)`,
                    pointerEvents: "none",
                  }}
                />
                <motion.span
                  animate={{ scale: [1, 1.15, 1], opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  style={{ fontSize: 13 }}
                >{wallet.icon}</motion.span>
                <span className="hidden md:inline">
                  {wallet.address.slice(0, 4)}…{wallet.address.slice(-3)}
                </span>
                {exchanges.length > 0 && (
                  <span className="pk text-[8px] px-1 ml-1 border rounded-sm"
                        style={{ color: "var(--accent-cyan)", borderColor: "var(--accent-cyan)" }}>
                    +{exchanges.length}
                  </span>
                )}
              </motion.button>
            ) : (
              /* No wallet — CLICKABLE neon pill that opens WalletConnectModal. */
              <motion.button
                whileHover={{ scale: 1.06, y: -1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => { audio.click?.(); setWalletOpen(true) }}
                aria-label="Connect wallet or exchange"
                animate={{
                  boxShadow: [
                    "0 0 6px rgba(0,255,255,0.3), inset 0 0 4px rgba(0,255,255,0.12)",
                    "0 0 14px rgba(0,255,255,0.7), inset 0 0 8px rgba(0,255,255,0.25)",
                    "0 0 6px rgba(0,255,255,0.3), inset 0 0 4px rgba(0,255,255,0.12)",
                  ],
                }}
                transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
                className="pk text-[9px] md:text-[10px] tracking-widest px-3 py-1.5 border-2 min-h-touch flex items-center gap-1.5 flex-shrink-0 relative overflow-hidden"
                style={{
                  color: "var(--accent-cyan)",
                  borderColor: "var(--accent-cyan)",
                  background: "linear-gradient(135deg, rgba(0,255,255,0.14), rgba(0,255,255,0.04))",
                  textShadow: "0 0 6px rgba(0,255,255,0.7)",
                  borderRadius: 4,
                  cursor: "pointer",
                }}
                title="Connect wallet or exchange"
              >
                {/* shimmer sweep */}
                <motion.span
                  aria-hidden
                  animate={{ x: ["-150%", "200%"] }}
                  transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
                  style={{
                    position: "absolute", inset: 0,
                    background: "linear-gradient(90deg, transparent, rgba(0,255,255,0.35), transparent)",
                    pointerEvents: "none",
                  }}
                />
                <motion.span
                  animate={{ rotate: [0, 12, -12, 0] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  style={{ display: "inline-block" }}
                >◆</motion.span>
                <span className="hidden xs:inline md:inline">CONNECT</span>
              </motion.button>
            )
          )}
        </div>
      </nav>

      {/* spacer for fixed nav */}
      <div aria-hidden style={{ height: 76 }} />

      <WalletConnectModal open={walletOpen} onClose={() => setWalletOpen(false)} />
      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />

      {/* Phase A 2026-05-11: mobile hamburger drawer (mobile-only via internal md:hidden) */}
      <MobileNav
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
        links={LINKS}
        pathname={pathname}
        session={session}
        onLinkClick={(l, e) => handleLink(l, e)}
      />
    </>
  )
}
