import { useEffect, useRef, useState } from "react"

function fmtHMS(total) {
  const h = Math.floor(total/3600).toString().padStart(2,"0")
  const m = Math.floor((total%3600)/60).toString().padStart(2,"0")
  const s = Math.floor(total%60).toString().padStart(2,"0")
  return `${h}:${m}:${s}`
}

export default function LiveClock() {
  const [now, setNow] = useState(new Date())
  const start = useRef(Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  const uptime = Math.floor((Date.now() - start.current) / 1000)
  return (
    <div className="flex items-center gap-4 pk text-[7px] text-[color:var(--subdim)] tracking-widest">
      <span className="inline-flex items-center gap-2">
        <span className="w-2 h-2 bg-[color:var(--green)]" style={{ animation: "qwr-blink 1s infinite", boxShadow: "0 0 6px var(--green)" }} />
        LIVE
      </span>
      <span className="text-[color:var(--text)]">{now.toISOString().replace("T"," ").slice(0,19)}</span>
      <span>UPTIME {fmtHMS(uptime)}</span>
    </div>
  )
}
