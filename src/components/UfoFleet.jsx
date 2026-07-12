import { useEffect, useState, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"

// ── Pixel-art UFO sprite ──────────────────────────────
function UfoSprite({ size = 40, body = "#00ddcc", dome = "#88ff00", lights = "#ffff00" }) {
  const s = size / 16
  const rect = (x, y, w = 1, h = 1, fill) => (
    <rect key={`${x}-${y}-${fill}`} x={x*s} y={y*s} width={w*s} height={h*s} fill={fill} />
  )
  return (
    <svg
      width={size}
      height={size * (12/16)}
      viewBox={`0 0 ${size} ${size*(12/16)}`}
      style={{ imageRendering: "pixelated", display: "block" }}
      aria-hidden
    >
      {/* dome */}
      {rect(6, 0, 4, 1, dome)}
      {rect(5, 1, 6, 1, dome)}
      {rect(5, 2, 1, 1, dome)}
      {rect(6, 2, 4, 1, "#ffffff")}
      {rect(10, 2, 1, 1, dome)}
      {/* body upper */}
      {rect(3, 3, 10, 1, body)}
      {/* body middle with portholes */}
      {rect(2, 4, 1, 1, body)}
      {rect(3, 4, 1, 1, lights)}
      {rect(4, 4, 2, 1, body)}
      {rect(6, 4, 1, 1, lights)}
      {rect(7, 4, 2, 1, body)}
      {rect(9, 4, 1, 1, lights)}
      {rect(10, 4, 2, 1, body)}
      {rect(12, 4, 1, 1, lights)}
      {rect(13, 4, 1, 1, body)}
      {/* body bottom */}
      {rect(1, 5, 14, 1, body)}
      {rect(0, 6, 16, 1, "#0b1525")}
      {rect(2, 6, 12, 1, body)}
      {/* shadow / underside */}
      {rect(4, 7, 8, 1, "#080f1e")}
      {rect(6, 8, 4, 1, "#080f1e")}
    </svg>
  )
}

// Possible color schemes for variety
const SCHEMES = [
  { body: "#00ddcc", dome: "#88ff00", lights: "#ffff00" },
  { body: "#cc44ff", dome: "#00ffff", lights: "#ff5577" },
  { body: "#ff8800", dome: "#ffff00", lights: "#00ff41" },
  { body: "#00ff41", dome: "#00ffff", lights: "#ff00ff" },
]

const rand = (a, b) => a + Math.random() * (b - a)
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)]

let idCounter = 0

function makeUfo() {
  const fromLeft = Math.random() < 0.5
  const scheme = pick(SCHEMES)
  // Varied sizes — tiny scouts to huge motherships
  const sizeRoll = Math.random()
  let size
  if      (sizeRoll < 0.25) size = Math.floor(rand(32, 50))    // small
  else if (sizeRoll < 0.65) size = Math.floor(rand(55, 85))    // medium
  else if (sizeRoll < 0.90) size = Math.floor(rand(90, 130))   // large
  else                      size = Math.floor(rand(140, 180))  // huge mothership
  return {
    id: ++idCounter,
    phase: "cruise",
    fromLeft,
    scheme,
    size,
    y: rand(8, 75),
    vx: rand(0.3, 0.7) * (fromLeft ? 1 : -1),  // slower
    cruiseBob: rand(0.3, 0.9),
    landX: rand(20, 80),
    landY: rand(30, 80),
    bornAt: Date.now(),
    willLand: Math.random() < 0.4,
  }
}

// ── Single UFO actor with lifecycle ───────────────────
function Ufo({ init, onGone }) {
  const [phase, setPhase] = useState("enter")
  const [x, setX] = useState(init.fromLeft ? -10 : 110)
  const [y, setY] = useState(init.y)
  const tRef = useRef(null)

  // Lifecycle driver
  useEffect(() => {
    const target = init.willLand ? init.landX : (init.fromLeft ? 110 : -10)

    // Enter: cruise onto screen
    setPhase("cruise")
    setX(target)
    setY(init.willLand ? init.landY - 10 : init.y)

    if (init.willLand) {
      // After cruise, descend & land
      tRef.current = setTimeout(() => {
        setPhase("descend")
        setY(init.landY)
      }, 6000)

      tRef.current = setTimeout(() => {
        setPhase("landed")
      }, 8000)

      tRef.current = setTimeout(() => {
        setPhase("ascend")
        setY(init.landY - 12)
      }, 12000 + rand(0, 3000))

      tRef.current = setTimeout(() => {
        setPhase("leave")
        setX(init.fromLeft ? 115 : -15)
        setY(Math.max(5, init.landY - 30))
      }, 14500)

      tRef.current = setTimeout(() => onGone(init.id), 19000)
    } else {
      tRef.current = setTimeout(() => onGone(init.id), 14000)
    }

    return () => clearTimeout(tRef.current)
  }, [])

  const cruise = phase === "cruise"
  const descending = phase === "descend"
  const landed = phase === "landed"
  const ascending = phase === "ascend"
  const leaving = phase === "leave"

  const duration =
    cruise ? 6 :
    descending ? 2 :
    ascending ? 1.8 :
    leaving ? 4 :
    1

  return (
    <motion.div
      className="absolute pointer-events-none"
      style={{ left: `${x}%`, top: `${y}%` }}
      initial={{ left: `${init.fromLeft ? -10 : 110}%`, top: `${init.y}%` }}
      animate={{ left: `${x}%`, top: `${y}%` }}
      transition={{
        duration,
        ease: cruise ? "linear" : descending ? "easeInOut" : ascending ? "easeOut" : "easeIn",
      }}
    >
      {/* Subtle bob while cruising */}
      <motion.div
        animate={cruise
          ? { y: [0, -4, 0, 4, 0] }
          : { y: 0 }
        }
        transition={{ duration: 2.4, repeat: cruise ? Infinity : 0, ease: "easeInOut" }}
      >
        <div className="relative">
          {/* Glow */}
          <div
            className="absolute inset-0 -z-10"
            style={{
              filter: `blur(12px)`,
              background: `radial-gradient(circle, ${init.scheme.body}55, transparent 70%)`,
              transform: `translate(-10%, -10%) scale(1.4)`,
            }}
          />

          {/* UFO sprite */}
          <UfoSprite
            size={init.size}
            body={init.scheme.body}
            dome={init.scheme.dome}
            lights={init.scheme.lights}
          />

          {/* Abduction beam when landed */}
          <AnimatePresence>
            {(landed || descending) && (
              <motion.div
                initial={{ opacity: 0, scaleY: 0.4 }}
                animate={{
                  opacity: landed ? [0.35, 0.7, 0.35] : 0.4,
                  scaleY: landed ? 1 : 0.8,
                }}
                exit={{ opacity: 0, scaleY: 0 }}
                transition={{
                  duration: landed ? 1.2 : 0.5,
                  repeat: landed ? Infinity : 0,
                  ease: "easeInOut",
                }}
                className="absolute left-1/2 -translate-x-1/2 pointer-events-none"
                style={{
                  top: init.size * 0.7,
                  width: init.size * 0.9,
                  height: init.size * 2.2,
                  background: `linear-gradient(to bottom, ${init.scheme.lights}aa, ${init.scheme.lights}00)`,
                  clipPath: "polygon(30% 0, 70% 0, 100% 100%, 0 100%)",
                  transformOrigin: "top center",
                }}
              />
            )}
          </AnimatePresence>

          {/* "LANDED!" bubble */}
          <AnimatePresence>
            {landed && (
              <motion.div
                initial={{ opacity: 0, y: 6, scale: 0.8 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0 }}
                className="absolute left-1/2 -translate-x-1/2 pk text-[7px] px-1 py-0.5 border whitespace-nowrap"
                style={{
                  top: -14,
                  color: init.scheme.dome,
                  borderColor: init.scheme.dome,
                  background: init.scheme.dome + "18",
                  boxShadow: `0 0 6px ${init.scheme.dome}88`,
                  letterSpacing: 1.2,
                }}
              >
                ★ LANDED
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </motion.div>
  )
}

// ── Fleet manager ──────────────────────────────────────
export default function UfoFleet({ max = 5 }) {
  const [ufos, setUfos] = useState([])

  useEffect(() => {
    // Spawn 2 initial UFOs quickly
    const first = setTimeout(() => {
      setUfos(u => u.length < max ? [...u, makeUfo()] : u)
    }, 1500)
    const second = setTimeout(() => {
      setUfos(u => u.length < max ? [...u, makeUfo()] : u)
    }, 5000)

    const t = setInterval(() => {
      setUfos(u => u.length < max ? [...u, makeUfo()] : u)
    }, 6000 + Math.random() * 5000)

    return () => { clearTimeout(first); clearTimeout(second); clearInterval(t) }
  }, [max])

  const remove = (id) => setUfos(u => u.filter(x => x.id !== id))

  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden"
      style={{ zIndex: 1 }}
    >
      {ufos.map(u => <Ufo key={u.id} init={u} onGone={remove} />)}
    </div>
  )
}
