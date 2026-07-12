// 8 pixel-art agent sprites — 12x12 grids rendered as SVG.
// Colors are passed in from the caller so we can recolor per theme.

const mkSprite = (pixels) =>
  function Sprite({ size = 32, color = "#34d399" }) {
    const s = size / 12
    const cell = (x, y, w = 1, h = 1, i) => (
      <rect key={i} x={x * s} y={y * s} width={w * s} height={h * s} fill={color} />
    )
    return (
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ imageRendering: "pixelated", display: "block" }}
        aria-hidden
      >
        {pixels.map((p, i) => cell(p[0], p[1], p[2] ?? 1, p[3] ?? 1, i))}
      </svg>
    )
  }

export const AlphaSprite = mkSprite([
  [4,0,4,1],[3,1,6,1],[2,2,8,1],[1,3,2,1],[4,3,4,1],[9,3,2,1],
  [1,4,10,1],[0,5,12,1],[1,6,10,1],[0,7,3,1],[4,7,4,1],[9,7,3,1],
  [1,8,2,1],[4,8,1,1],[7,8,1,1],[9,8,2,1],
  [0,9,2,1],[3,9,1,1],[8,9,1,1],[10,9,2,1],
])

export const SkepticSprite = mkSprite([
  [3,0,1,1],[5,0,2,1],[3,1,6,1],[2,2,8,1],[1,3,2,1],[3,3,1,1],[5,3,2,1],[8,3,1,1],[10,3,1,1],
  [1,4,10,1],[0,5,12,1],[2,6,8,1],[1,7,1,1],[4,7,4,1],[10,7,1,1],
  [0,8,2,1],[3,8,2,1],[7,8,2,1],[10,8,2,1],
  [1,9,1,1],[3,9,1,1],[8,9,1,1],[10,9,1,1],
])

export const RiskSprite = mkSprite([
  [4,0,4,1],[3,1,6,1],[2,2,8,1],[0,3,2,1],[3,3,6,1],[10,3,2,1],
  [0,4,12,1],[1,5,10,1],[2,6,8,1],[1,7,2,1],[4,7,4,1],[9,7,2,1],
  [0,8,3,1],[5,8,2,1],[9,8,3,1],
  [0,9,2,1],[10,9,2,1],
])

export const ExecutorSprite = mkSprite([
  [3,0,6,1],[2,1,8,1],[1,2,10,1],[0,3,12,1],[0,4,2,1],[4,4,4,1],[10,4,2,1],
  [0,5,12,1],[1,6,10,1],[0,7,4,1],[5,7,2,1],[8,7,4,1],
  [1,8,2,1],[4,8,1,1],[7,8,1,1],[9,8,2,1],
  [0,9,2,1],[4,9,1,1],[7,9,1,1],[10,9,2,1],
])

export const RegimeSprite = mkSprite([
  [5,0,2,1],[4,1,4,1],[2,2,8,1],[1,3,2,1],[5,3,2,1],[9,3,2,1],
  [0,4,12,1],[1,5,10,1],[0,6,12,1],[1,7,2,1],[3,7,6,1],[9,7,2,1],
  [0,8,2,1],[3,8,1,1],[5,8,2,1],[8,8,1,1],[10,8,2,1],
  [1,9,2,1],[9,9,2,1],
])

export const HunterSprite = mkSprite([
  [4,0,4,2],[3,1,1,1],[8,1,1,1],[1,2,2,1],[3,2,6,1],[9,2,2,1],
  [0,3,3,1],[4,3,4,1],[9,3,3,1],[0,4,12,1],[1,5,10,1],
  [2,6,8,1],[0,7,3,1],[4,7,4,1],[9,7,3,1],
  [0,8,2,1],[5,8,2,1],[10,8,2,1],
  [0,9,1,1],[5,9,2,1],[11,9,1,1],
])

export const ChampionSprite = mkSprite([
  [4,0,4,1],[3,1,1,1],[5,1,2,1],[8,1,1,1],
  [2,2,8,1],[0,3,2,1],[3,3,2,1],[7,3,2,1],[10,3,2,1],
  [0,4,12,1],[1,5,10,1],[0,6,12,1],
  [1,7,2,1],[4,7,4,1],[9,7,2,1],
  [0,8,2,1],[3,8,2,1],[7,8,2,1],[10,8,2,1],
  [1,9,1,1],[3,9,1,1],[8,9,1,1],[10,9,1,1],
])

export const RecoverySprite = mkSprite([
  [3,0,6,1],[2,1,8,1],[1,2,1,1],[3,2,1,1],[5,2,2,1],[8,2,1,1],[10,2,1,1],
  [1,3,10,1],[0,4,12,1],[1,5,10,1],[2,6,8,1],
  [0,7,3,1],[4,7,4,1],[9,7,3,1],
  [1,8,1,1],[4,8,4,1],[10,8,1,1],
  [0,9,2,1],[10,9,2,1],
])

// Institutional-theme colors (muted vs the original neon palette).
export const AGENTS = [
  { id: "alpha",    name: "ALPHA",    role: "Trade thesis",    Sprite: AlphaSprite,    color: "#22d3ee" }, // cyan
  { id: "skeptic",  name: "SKEPTIC",  role: "Attack thesis",   Sprite: SkepticSprite,  color: "#c084fc" }, // purple
  { id: "risk",     name: "RISK",     role: "Exposure check",  Sprite: RiskSprite,     color: "#fb923c" }, // orange
  { id: "executor", name: "EXECUTOR", role: "Order quality",   Sprite: ExecutorSprite, color: "#2dd4bf" }, // teal
  { id: "regime",   name: "REGIME",   role: "Market state",    Sprite: RegimeSprite,   color: "#facc15" }, // yellow
  { id: "hunter",   name: "HUNTER",   role: "Arb finder",      Sprite: HunterSprite,   color: "#f97316" }, // orange-2
  { id: "champion", name: "CHAMPION", role: "Elite signals",   Sprite: ChampionSprite, color: "#34d399" }, // green
  { id: "recovery", name: "RECOVERY", role: "Hedge mode",      Sprite: RecoverySprite, color: "#f472b6" }, // pink
]
