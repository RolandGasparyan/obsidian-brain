/**
 * TradingGuruLogo.jsx — Animated SVG logo for TRADING GURU brand.
 *
 * SIMPLIFIED 2026-05-13 17:55 — removed continuous rotation + heavy effects
 * that were causing visual issues. Now uses CSS-based subtle glow only.
 *
 * Re-creation of the operator's gold-orange spiral G logo as inline SVG.
 *
 * Animations:
 *   - CSS glow pulse (4s, low-overhead)
 *   - Hover: scale 1.08 + brighter glow
 *   - NO continuous rotation (was causing layout thrash)
 *
 * 2026-05-13 · Layer 3 brand asset · zero capital risk
 */

const KEYFRAMES_KEY = "tg-logo-keyframes-v2"

// Inject CSS once
function ensureCss() {
  if (typeof document === "undefined") return
  if (document.getElementById(KEYFRAMES_KEY)) return
  const style = document.createElement("style")
  style.id = KEYFRAMES_KEY
  style.textContent = `
    @keyframes tg-glow-pulse {
      0%, 100% { filter: drop-shadow(0 0 3px rgba(245,158,11,0.5)) drop-shadow(0 0 8px rgba(251,191,36,0.25)); }
      50%      { filter: drop-shadow(0 0 6px rgba(245,158,11,0.7)) drop-shadow(0 0 14px rgba(251,191,36,0.4)); }
    }
    .tg-logo-wrap {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      animation: tg-glow-pulse 4s ease-in-out infinite;
      transition: transform 0.25s ease;
    }
    .tg-logo-wrap:hover { transform: scale(1.08); }
    .tg-logo-wrap svg   { width: 100%; height: 100%; display: block; }
  `
  document.head.appendChild(style)
}

export default function TradingGuruLogo({
  size = 36,
  variant = "default",
  onClick,
  className = "",
  ariaLabel = "Trading Guru",
}) {
  ensureCss()
  const isMono = variant === "mono"
  const fillRef = isMono ? "currentColor" : "url(#tg-gold-gradient)"

  return (
    <span
      onClick={onClick}
      className={"tg-logo-wrap " + className}
      role="img"
      aria-label={ariaLabel}
      style={{
        width: size,
        height: size,
        cursor: onClick ? "pointer" : "default",
      }}
    >
      <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="tg-gold-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%"   stopColor="#fbbf24" />
            <stop offset="55%"  stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#ea7c30" />
          </linearGradient>
        </defs>

        {/* Outer C-ring: thick 270° arc forming the open G shape */}
        <g transform="translate(100 100)" fill="none" stroke={fillRef} strokeWidth="30" strokeLinecap="round" strokeLinejoin="round">
          {/* Outer ring with gap at upper-right (signature G opening) */}
          <path d="M 55,-60 A 80,80 0 1,0 60,60" />
          {/* Inner horizontal bar + curl forming G distinctive feature */}
          <path d="M 0,5 L 55,5 L 55,40 A 22,22 0 0,1 22,55" />
        </g>
      </svg>
    </span>
  )
}

export function TradingGuruMark({ size = 24 }) {
  return <TradingGuruLogo size={size} />
}
