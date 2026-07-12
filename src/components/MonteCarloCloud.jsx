import { Canvas, useFrame } from "@react-three/fiber"
import { useRef } from "react"
import * as THREE from "three"

function PathCloud({ paths }) {
  const group = useRef()

  useFrame(() => {
    group.current.rotation.y += 0.001
  })

  return (
    <group ref={group}>
      {paths.map((path, idx) => {
        const geometry = new THREE.BufferGeometry()
        const vertices = new Float32Array(path.length * 3)

        for (let i = 0; i < path.length; i++) {
          vertices[i * 3] = i * 0.1
          vertices[i * 3 + 1] = path[i] * 0.0003
          vertices[i * 3 + 2] = 0
        }

        geometry.setAttribute(
          "position",
          new THREE.BufferAttribute(vertices, 3)
        )

        return (
          <line key={idx} geometry={geometry}>
            <lineBasicMaterial
              color="#00ffaa"
              transparent
              opacity={0.1}
            />
          </line>
        )
      })}
    </group>
  )
}

export default function MonteCarloCloud({ simulatedPaths }) {
  return (
    <div className="h-96">
      <Canvas camera={{ position: [5, 3, 10] }}>
        <ambientLight intensity={0.5} />
        <PathCloud paths={simulatedPaths} />
      </Canvas>
    </div>
  )
}
