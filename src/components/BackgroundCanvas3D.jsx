import { Canvas, useFrame } from "@react-three/fiber"
import { useMemo, useRef } from "react"
import * as THREE from "three"
import { useApp } from "../state/AppContext.jsx"

function GridWave({ intensity, regime }) {
  const ref = useRef()
  const size = 40, seg = 60
  const geometry = useMemo(() => new THREE.PlaneGeometry(size, size, seg, seg), [])

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const pos = ref.current.geometry.attributes.position
    const amp = 0.6 + intensity * 1.4
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), y = pos.getY(i)
      const z = Math.sin(x * 0.35 + t * 0.8) * 0.3 * amp
              + Math.cos(y * 0.5  + t * 0.5) * 0.25 * amp
      pos.setZ(i, z)
    }
    pos.needsUpdate = true
    ref.current.rotation.z = t * 0.02
  })

  // regime 0=red, 0.5=amber, 1=green
  const hue = 0.02 + regime * 0.33  // 0.02 (red) → 0.35 (green-ish)
  const color = new THREE.Color().setHSL(hue, 0.6, 0.45)

  return (
    <mesh ref={ref} geometry={geometry} rotation={[-Math.PI / 2.1, 0, 0]} position={[0, -2, 0]}>
      <meshBasicMaterial color={color} wireframe transparent opacity={0.25} />
    </mesh>
  )
}

export default function BackgroundCanvas3D() {
  const { state, prefs } = useApp()
  if (!prefs.threeD) return null

  const volatility = Math.min(1, Math.abs(state.pnl) / 200)
  const regime     = state.regime

  return (
    <div className="fixed inset-0 -z-10 pointer-events-none">
      <Canvas
        dpr={[1, 1.5]}
        camera={{ position: [0, 6, 10], fov: 55 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.6} />
        <GridWave intensity={volatility + 0.2} regime={regime} />
        {/* Vignette-ish gradient via fog */}
        <fog attach="fog" args={["#000", 8, 22]} />
      </Canvas>
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/80" />
    </div>
  )
}
