import { useEffect, useRef } from "react"

export default function CursorSpotlight() {
  const ref = useRef(null)
  useEffect(() => {
    let raf = 0
    let tx = 0, ty = 0, x = 0, y = 0
    const onMove = (e) => { tx = e.clientX; ty = e.clientY }
    const loop = () => {
      x += (tx - x) * 0.12
      y += (ty - y) * 0.12
      if (ref.current) {
        ref.current.style.background =
          `radial-gradient(500px circle at ${x}px ${y}px, rgba(52,211,153,0.07), transparent 60%)`
      }
      raf = requestAnimationFrame(loop)
    }
    window.addEventListener("mousemove", onMove)
    raf = requestAnimationFrame(loop)
    return () => { cancelAnimationFrame(raf); window.removeEventListener("mousemove", onMove) }
  }, [])
  return <div ref={ref} className="fixed inset-0 pointer-events-none z-[5]" />
}
