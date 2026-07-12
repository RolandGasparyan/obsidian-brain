import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import { audio } from "../ui/audio_engine.js"
import { useApp } from "../state/AppContext.jsx"

// ── Elegant classic pixel UFO — refined, cleaner, cuter ──
function UfoLogo({ size = 160, tick = 0 }) {
  const W = 30, H = 18
  const px = (a, b, w = 1, h = 1, c) => (
    <rect key={`${a}-${b}-${c}-${w}-${h}`} x={a} y={b} width={w} height={h} fill={c} />
  )

  // Refined chrome body palette
  const chromeLt  = "#b8f8ef"    // top highlight
  const chromeMid = "#2fd4c4"    // main
  const chromeDk  = "#0d7a73"    // shadow
  const chromeBk  = "#063c39"    // deep bottom
  const glass     = "#a0f5d4"    // dome glass
  const glassLt   = "#e6fff5"    // dome highlight
  const glassDk   = "#3caa80"    // dome shadow
  const alien     = "#8cff4a"    // alien skin
  const alienDk   = "#4a9a20"    // alien shadow
  const darkLine  = "#0a1020"    // rim/outline

  // Refined porthole palette — 4 colors, slow pulse per porthole
  const portOn  = ["#ffd93d", "#ff7a90", "#6fe0ff", "#d98bff"]
  const portOff = ["#c2a12a", "#b85868", "#4f9dbf", "#9b62bf"]
  const port = (i, on) => (on ? portOn[i % 4] : portOff[i % 4])

  // Alien blinks periodically
  const eyeOpen = tick % 14 !== 0

  // Warm rotating underlight (steady gold wash)
  const underGold = "#ffd060"

  return (
    <svg
      width={size}
      height={size * (H / W)}
      viewBox={`0 0 ${W} ${H}`}
      style={{
        imageRendering: "pixelated",
        filter: `
          drop-shadow(0 0 14px rgba(255,210,90,0.7))
          drop-shadow(0 0 30px rgba(47,212,196,0.45))
          drop-shadow(0 0 56px rgba(0,255,180,0.25))
        `,
      }}
    >
      {/* ── Outline / shadow silhouette ── */}
      {/* dome outline */}
      {px(12, 0, 6, 1, darkLine)}
      {px(11, 1, 1, 1, darkLine)}{px(18, 1, 1, 1, darkLine)}
      {px(10, 2, 1, 1, darkLine)}{px(19, 2, 1, 1, darkLine)}
      {px( 9, 3, 1, 1, darkLine)}{px(20, 3, 1, 1, darkLine)}
      {px( 8, 4, 1, 1, darkLine)}{px(21, 4, 1, 1, darkLine)}

      {/* ── DOME glass ── */}
      {px(12, 1, 6, 1, glass)}
      {px(11, 2, 8, 1, glass)}
      {px(10, 3, 10, 1, glass)}
      {px( 9, 4, 12, 1, glass)}
      {/* dome bottom shadow */}
      {px( 9, 4, 12, 1, glass)}
      {/* glossy highlight */}
      {px(12, 1, 2, 1, glassLt)}
      {px(11, 2, 1, 1, glassLt)}
      {px(11, 3, 1, 1, glassLt)}
      {/* dome inner shadow */}
      {px(18, 3, 2, 1, glassDk)}
      {px(19, 4, 1, 1, glassDk)}

      {/* ── cute ALIEN inside dome ── */}
      {/* antennae (two) */}
      {px(13, 0, 1, 1, darkLine)}{px(16, 0, 1, 1, darkLine)}
      {px(13.2, -0.4, 0.6, 0.6, tick % 2 ? "#ffff66" : "#ffaa00")}
      {px(16.2, -0.4, 0.6, 0.6, tick % 2 ? "#ffaa00" : "#ffff66")}
      {/* head */}
      {px(13, 2, 4, 1, alien)}
      {px(12, 3, 6, 1, alien)}
      {px(12, 3, 1, 1, alienDk)}
      {px(17, 3, 1, 1, alienDk)}
      {/* big round eyes */}
      {eyeOpen ? (
        <>
          {/* left eye */}
          {px(13, 3, 1, 1, "#ffffff")}
          {px(13.4, 3.1, 0.4, 0.6, darkLine)}
          {/* right eye */}
          {px(16, 3, 1, 1, "#ffffff")}
          {px(16.4, 3.1, 0.4, 0.6, darkLine)}
        </>
      ) : (
        <>
          {px(13, 3.4, 1, 0.3, darkLine)}
          {px(16, 3.4, 1, 0.3, darkLine)}
        </>
      )}
      {/* small smile */}
      {px(14, 4, 2, 0.4, alienDk)}

      {/* ── CHROME body: three layers ── */}
      {/* top rim (bright) */}
      {px( 6, 5, 18, 1, chromeLt)}
      {px( 7, 5,  1, 1, "#ffffff")}   /* chrome highlight */

      {/* disc with portholes (slow pulse — on for ~60% of the time) */}
      {px( 4, 6,  2, 1, chromeMid)}
      {px( 6, 6,  1, 1, port(0, tick % 6 < 4))}
      {px( 7, 6,  2, 1, chromeMid)}
      {px( 9, 6,  1, 1, port(1, tick % 6 < 4))}
      {px(10, 6,  2, 1, chromeMid)}
      {px(12, 6,  1, 1, port(2, tick % 6 < 4))}
      {px(13, 6,  4, 1, chromeMid)}
      {px(17, 6,  1, 1, port(3, tick % 6 < 4))}
      {px(18, 6,  2, 1, chromeMid)}
      {px(20, 6,  1, 1, port(0, tick % 6 < 4))}
      {px(21, 6,  2, 1, chromeMid)}
      {px(23, 6,  1, 1, port(1, tick % 6 < 4))}
      {px(24, 6,  2, 1, chromeMid)}

      {/* widest belly (darker edge) */}
      {px( 2, 7, 26, 1, chromeMid)}
      {px( 1, 8, 28, 1, darkLine)}
      {px( 2, 8, 26, 1, chromeMid)}

      {/* ── Bottom hull — tapered with beveled shading ── */}
      {px( 4, 9,  1, 1, darkLine)}
      {px( 5, 9, 20, 1, chromeDk)}
      {px(25, 9,  1, 1, darkLine)}
      {/* 2 navigation lights */}
      {px( 5, 9,  1, 1, "#ff5577")}          /* port red (left) */
      {px(24, 9,  1, 1, "#6fe0ff")}          /* starboard cyan (right) */

      {px( 7,10, 16, 1, chromeDk)}
      {px( 9,11, 12, 1, chromeBk)}
      {px(11,12,  8, 1, chromeBk)}
      {px(13,13,  4, 1, chromeBk)}

      {/* ── Central emitter dish (beam source) ── */}
      {px(13,13,  4, 1, "#ffe680")}
      {px(14,13,  2, 1, "#ffffff")}
      {/* warm ambient underglow on inner bottom */}
      {px(12,12,  6, 1, underGold + "66")}
    </svg>
  )
}

export default function CinematicIntro() {
  const { setIntro, prefs } = useApp()
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setTick((v) => v + 1), 180)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    audio.preloadSamples?.()
    // One sound at a time — no stacking

    // 0.3s — TRADING GURU reveal (short 0.6s blip)
    const t1 = setTimeout(() => { if (prefs.sound) audio.textReveal() }, 300)
    // 1.3s — AI TRADING CHAMPIONSHIP reveal (another short blip, 1s after t1)
    const t2 = setTimeout(() => { if (prefs.sound) audio.textReveal() }, 1300)

    // 3.5s — Landing MP3 starts here so its IMPACT tail coincides with UFO touchdown at 9.4s.
    // We schedule now, actual playback offset is computed from MP3 duration vs remaining 5900ms.
    const syncT = setTimeout(() => {
      if (prefs.sound) audio.ufoLandingSync?.(5900, 200)
    }, 3500)

    // 10.0s — Beam activation sound (600ms AFTER touchdown so nothing overlaps)
    const t4 = setTimeout(() => { if (prefs.sound) audio.beamOn() }, 10000)

    // 12.5s — Triumph chord (2.5s after beam, clean space)
    const t5 = setTimeout(() => { if (prefs.sound) audio.triumph() }, 12500)

    // 15s — intro exits
    const t6 = setTimeout(() => setIntro(false), 15000)

    // Any key / click dismisses intro
    const dismiss = () => setIntro(false)
    window.addEventListener("keydown", dismiss)
    window.addEventListener("pointerdown", dismiss)

    return () => {
      [t1, t2, syncT, t4, t5, t6].forEach(clearTimeout)
      window.removeEventListener("keydown", dismiss)
      window.removeEventListener("pointerdown", dismiss)
    }
  }, [])

  const gapBelowUfo = 220       // vertical gap between UFO bottom and TRADING GURU (shorter — proportional)
  const beamHeight  = gapBelowUfo    // beam fills exactly the gap — stops at TRADING GURU top

  // Small smoke puffs within the short beam (golden/amber hues) — AFTER UFO lands
  const smokePuffs = useMemo(
    () => Array.from({ length: 10 }, (_, i) => ({
      id: i,
      left: (Math.random() - 0.5) * 80,
      duration: 1.4 + Math.random() * 0.8,
      delay: 9.8 + i * 0.18,           /* starts only after beam activates at 9.4s */
      size: 6 + Math.random() * 10,
      hue: 40 + Math.random() * 20,
    })),
    []
  )

  return (
    <motion.div
      initial={{ opacity: 1 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.6 }}
      className="fixed inset-0 z-[100] bg-[color:var(--bg)] flex items-center justify-center"
    >
      <div className="relative text-center" style={{ width: 1000, maxWidth: "96vw" }}>

        {/* ── UFO + beam + smoke descend together ── */}
        <motion.div
          initial={{ y: -800, opacity: 0, scale: 0.4 }}
          animate={{ y: 12, opacity: 1, scale: 1 }}     /* stays HIGH UP — only tiny drop */
          transition={{
            duration: 7.8,              /* 50% slower — very graceful descent */
            delay: 1.6,
            ease: [0.22, 0.61, 0.36, 1],
          }}
          className="flex justify-center relative"
          style={{ zIndex: 2 }}
        >
          <motion.div
            className="relative"
            animate={{ y: [0, -4, 0], rotate: [-1.5, 1.5, -1.5] }}
            transition={{
              y: { duration: 4.2, repeat: Infinity, ease: "easeInOut", delay: 9.4 },
              rotate: { duration: 4.2, repeat: Infinity, ease: "easeInOut", delay: 9.4 },
            }}
          >
            {/* Color-cycling halo glow — bigger, brighter */}
            <motion.div
              className="absolute -inset-14 blur-2xl pointer-events-none"
              animate={{
                opacity: [0.4, 0.85, 0.4],
                scale: [0.95, 1.1, 0.95],
              }}
              transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
              style={{
                background: `
                  radial-gradient(circle,
                    hsla(${(tick * 12) % 360}, 90%, 65%, 0.55),
                    rgba(0,255,65,0.25) 40%,
                    transparent 70%)
                `,
              }}
            />
            <UfoLogo size={220} tick={tick} />

            {/* ── BEAM — travels with UFO, shining from the start ── */}
            <motion.div
              className="absolute left-1/2 pointer-events-none"
              initial={{ opacity: 0, scaleY: 0.1 }}
              animate={{ opacity: [0, 0, 0.95, 0.95], scaleY: [0.1, 0.1, 1, 1] }}
              transition={{
                duration: 1.0,
                delay: 9.4,             /* activates only AFTER UFO lands */
                times: [0, 0.05, 0.9, 1],
                ease: "easeOut",
              }}
              style={{
                top: "100%",            // anchored to UFO underside
                marginTop: 0,
                width: 320,
                height: beamHeight,
                marginLeft: -160,
                background:
                  "linear-gradient(to bottom, rgba(255,240,140,0.95), rgba(255,200,40,0.8) 30%, rgba(255,170,20,0.65) 65%, rgba(255,140,0,0.4) 100%)",
                transformOrigin: "top center",
                clipPath: "polygon(30% 0, 70% 0, 100% 100%, 0 100%)",     /* balanced trapezoid */
                filter: "drop-shadow(0 0 32px rgba(255,210,60,0.85)) drop-shadow(0 0 60px rgba(255,180,20,0.5))",
                WebkitMaskImage:
                  "linear-gradient(to bottom, black 0%, black 85%, transparent 100%)",
                maskImage:
                  "linear-gradient(to bottom, black 0%, black 85%, transparent 100%)",
                zIndex: 1,
              }}
            />

            {/* Pulsing descent rings in beam — activate AFTER UFO lands */}
            {[0, 1, 2, 3].map((i) => (
              <motion.div
                key={i}
                className="absolute left-1/2 pointer-events-none"
                initial={{ opacity: 0, top: "100%" }}
                animate={{
                  opacity: [0, 0.85, 0],
                  top: ["100%", `calc(100% + ${beamHeight - 10}px)`],
                }}
                transition={{
                  duration: 1.2,
                  delay: 9.8 + i * 0.25,
                  repeat: Infinity,
                  repeatDelay: 0.2,
                  ease: "easeIn",
                }}
                style={{
                  width: 180,
                  marginLeft: -90,
                  height: 4,
                  background:
                    "linear-gradient(to right, transparent, rgba(255,255,255,0.95), transparent)",
                  filter: "blur(0.5px)",
                  zIndex: 3,
                }}
              />
            ))}

            {/* ── SMOKE/FOG puffs rising within the beam ── */}
            {smokePuffs.map((p) => (
              <motion.div
                key={p.id}
                className="absolute left-1/2 pointer-events-none"
                initial={{
                  top: `calc(100% + ${beamHeight - 20}px)`,
                  opacity: 0,
                  scale: 0.5,
                }}
                animate={{
                  top: [`calc(100% + ${beamHeight - 20}px)`, "100%"],
                  opacity: [0, 0.6, 0],
                  scale: [0.5, 1.4, 1.8],
                }}
                transition={{
                  duration: p.duration,
                  delay: p.delay,
                  repeat: Infinity,
                  repeatDelay: 0.6,
                  ease: "easeOut",
                }}
                style={{
                  width: p.size,
                  height: p.size,
                  marginLeft: p.left - p.size / 2,
                  background: `radial-gradient(circle, hsla(${p.hue}, 80%, 75%, 0.55), hsla(${p.hue}, 80%, 60%, 0) 70%)`,
                  borderRadius: "50%",
                  filter: "blur(3px)",
                  zIndex: 2,
                }}
              />
            ))}
          </motion.div>
        </motion.div>

        {/* ── Spacer — creates the vertical gap where the beam lands ── */}
        <div style={{ height: gapBelowUfo }} aria-hidden />

        {/* ── TRADING GURU — appears first (GREEN same as championship) ── */}
        <motion.div
          initial={{ opacity: 0, letterSpacing: "0.6em", y: 12 }}
          animate={{ opacity: 1, letterSpacing: "0.25em", y: 0 }}
          transition={{ delay: 0.3, duration: 0.9, ease: [0.22, 0.61, 0.36, 1] }}
          className="pk text-xl md:text-3xl text-[color:var(--green)] relative whitespace-nowrap"
          style={{
            zIndex: 4,
            textShadow:
              "0 0 18px rgba(0,255,65,0.85), 0 0 36px rgba(0,255,65,0.55), 0 0 60px rgba(0,255,200,0.4)",
          }}
        >
          TRADING GURU
        </motion.div>

        {/* ── AI TRADING CHAMPIONSHIP — appears second ── */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.8 }}
          className="pk text-2xl md:text-4xl text-[color:var(--green)] mt-5 relative whitespace-nowrap"
          style={{
            zIndex: 4,
            textShadow:
              "0 0 20px rgba(0,255,65,0.75), 0 0 40px rgba(0,255,65,0.45), 0 0 80px rgba(0,255,200,0.3)",
          }}
        >
          AI TRADING CHAMPIONSHIP
        </motion.div>

        <motion.div
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ delay: 12.2, duration: 0.7, ease: "easeInOut" }}
          className="mt-8 mx-auto h-0.5 w-64 origin-left relative"
          style={{
            zIndex: 4,
            background: "linear-gradient(90deg, transparent, var(--green), transparent)",
          }}
        />

        {/* PRESS ANY KEY TO LOG START */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.3, 1, 0.3, 1] }}
          transition={{ delay: 12.8, duration: 2.2, repeat: Infinity, repeatDelay: 0.2 }}
          className="mt-6 pk text-[10px] tracking-widest text-[color:var(--green)] relative"
          style={{
            zIndex: 4,
            textShadow: "0 0 10px rgba(0,255,65,0.7), 0 0 20px rgba(0,255,65,0.4)",
          }}
        >
          ► PRESS ANY KEY TO LOG START
        </motion.div>

      </div>
    </motion.div>
  )
}
