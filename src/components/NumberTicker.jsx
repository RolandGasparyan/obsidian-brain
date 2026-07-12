import { useEffect } from "react"
import { motion, useMotionValue, useTransform, animate } from "framer-motion"

export default function NumberTicker({
  value,
  format = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 0 }),
  duration = 0.6,
  className = "",
}) {
  const mv = useMotionValue(value)
  const text = useTransform(mv, (v) => format(v))

  useEffect(() => {
    const controls = animate(mv, value, { duration, ease: [0.22, 0.61, 0.36, 1] })
    return () => controls.stop()
  }, [value, duration])

  return <motion.span className={className}>{text}</motion.span>
}
