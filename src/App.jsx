import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"

import { AppProvider, useApp } from "./state/AppContext.jsx"
import { useEventFX } from "./ui/useEventFX.js"

import ConfidenceGraph   from "./components/ConfidenceGraph.jsx"
import RegimeGauge       from "./components/RegimeGauge.jsx"
import CapitalCountdown  from "./components/CapitalCountdown.jsx"
import SharpeHeatMap     from "./components/SharpeHeatMap.jsx"
import SurvivalGauge     from "./components/SurvivalGauge.jsx"
import LatencyRadar      from "./components/LatencyRadar.jsx"
import ExecutionQuality  from "./components/ExecutionQuality.jsx"
import InteractiveCard   from "./components/InteractiveCard.jsx"
import NumberTicker      from "./components/NumberTicker.jsx"
import CinematicIntro    from "./components/CinematicIntro.jsx"
import SettingsPanel     from "./components/SettingsPanel.jsx"
import EventEffects      from "./components/EventEffects.jsx"
import ParticleDrift     from "./components/ParticleDrift.jsx"
import ConfidenceRing    from "./components/ConfidenceRing.jsx"
import EquityCurve       from "./components/EquityCurve.jsx"
import TickerTape        from "./components/TickerTape.jsx"
import LiveClock         from "./components/LiveClock.jsx"
import CommandPalette    from "./components/CommandPalette.jsx"
import AgentArena        from "./components/AgentArena.jsx"
import ActivityLog       from "./components/ActivityLog.jsx"
import SpaceBackground   from "./components/SpaceBackground.jsx"
import UfoFleet          from "./components/UfoFleet.jsx"
import XpCombo           from "./components/XpCombo.jsx"
import { AGENTS }        from "./components/AgentSprites.jsx"

function useConfidenceSeries() {
  const { state } = useApp()
  const [series, setSeries] = useState(() =>
    Array.from({ length: 60 }, (_, i) => ({ t: i, confidence: 0.5 })))
  useEffect(() => {
    setSeries(s => [...s.slice(-59), { t: s[s.length-1].t + 1, confidence: state.confidence }])
  }, [state.confidence])
  return series
}

function useEquitySeries() {
  const { state } = useApp()
  const [series, setSeries] = useState(() =>
    Array.from({ length: 60 }, (_, i) => ({ t: i, equity: state.balance })))
  useEffect(() => {
    setSeries(s => [...s.slice(-59), { t: s[s.length-1].t + 1, equity: state.balance }])
  }, [state.balance])
  return series
}

function useAgentConvictions() {
  const { state } = useApp()
  const [c, setC] = useState(() =>
    AGENTS.reduce((a, x) => { a[x.id] = 0.3 + Math.random()*0.5; return a }, {}))
  const [active, setActive] = useState("alpha")

  useEffect(() => {
    const t = setInterval(() => {
      setC(prev => {
        const next = { ...prev }
        for (const a of AGENTS) {
          const drift = (Math.random() - 0.5) * 0.14
          next[a.id] = Math.max(0.05, Math.min(1, next[a.id] + drift))
        }
        // bias by global regime confidence
        next.regime = Math.max(next.regime, state.regime)
        next.alpha  = Math.max(next.alpha, state.confidence)
        return next
      })
    }, 1300)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    // rotate "speaker" to agent with highest conviction
    const top = AGENTS.reduce((best, a) => c[a.id] > c[best.id] ? a : best, AGENTS[0])
    setActive(top.id)
  }, [c])

  return { convictions: c, active, setActive }
}

function Dashboard() {
  useEventFX()
  const { state, prefs, intro } = useApp()
  const confSeries   = useConfidenceSeries()
  const equitySeries = useEquitySeries()
  const { convictions, active, setActive } = useAgentConvictions()

  const pageVariants = prefs.reducedMotion
    ? { initial: { opacity: 1 }, animate: { opacity: 1 } }
    : {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.22,0.61,0.36,1] } },
      }

  return (
    <div className="relative min-h-screen qwr-crt">
      {/* SpaceBackground + UfoFleet + CinematicIntro now managed by the Shell in main.jsx */}
      <CommandPalette />
      <SettingsPanel />
      <EventEffects />
      <ParticleDrift />

      <motion.div
        variants={pageVariants}
        initial="initial"
        animate="animate"
        className="relative z-10 min-h-screen px-3 sm:px-4 md:px-6 pt-16 pb-8 space-y-4 max-w-[1800px] mx-auto"
      >
        {/* ── Header ── */}
        <header className="qwr-panel px-3 sm:px-4 py-3">
          <div className="flex items-center justify-between flex-wrap gap-3 md:gap-4">
            <div className="flex items-center gap-3 flex-wrap">
              <div
                className="pk text-[9px] sm:text-[10px] text-[color:var(--green)] tracking-widest"
                style={{ textShadow: "0 0 8px rgba(0,255,65,0.5)" }}
              >
                ►► QUANT WAR ROOM
              </div>
              <span className="pk text-[7px] text-[color:var(--subdim)] tracking-widest hidden sm:inline">V0.1 · EXECUTION MODE</span>
            </div>
            <div className="hidden md:block"><XpCombo /></div>
            <div className="hidden lg:block"><LiveClock /></div>
            <div className="text-right">
              <div className="pk text-[7px] text-[color:var(--subdim)] tracking-widest">BALANCE</div>
              <div
                className="pk text-[14px] sm:text-[18px] text-[color:var(--green)]"
                style={{ textShadow: "0 0 8px rgba(0,255,65,0.5)" }}
              >
                $<NumberTicker value={state.balance} format={v => v.toFixed(2)} />
              </div>
            </div>
          </div>
        </header>

        {/* ── Ticker tape ── */}
        <TickerTape />

        {/* ── Hero: Agent Arena (full width) ── */}
        <AgentArena
          activeId={active}
          convictions={convictions}
          onSelectAgent={setActive}
        />

        {/* ── KPI row 1 — 6 tiles including Regime + Confidence ── */}
        <section className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 md:gap-4">
          <RegimeGauge     value={state.regime} />
          <ConfidenceRing  value={state.confidence} />
          <CapitalCountdown balance={state.balance} />
          <SurvivalGauge   probability={state.survival} />
          <LatencyRadar    latencyMs={state.latency} />
          <SharpeHeatMap   sharpe={state.sharpe} />
        </section>

        {/* ── KPI row 2 — spans matching row 1 width on xl ── */}
        <section className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 md:gap-4">
          <div className="xl:col-span-2"><ExecutionQuality slippage={state.slippage} spread={state.spread} /></div>
          <div className="xl:col-span-2"><InteractiveCard
            title="WIN / LOSS"
            tooltip="Realized trade outcomes this session"
            accent="#00ff41"
            expanded={
              <div className="space-y-1 mono">
                <div>Trades: {state.trades}</div>
                <div>Wins:   {state.wins}</div>
                <div>Losses: {state.losses}</div>
                <div>Net PnL: ${state.pnl.toFixed(2)}</div>
              </div>
            }
          >
            <div className="flex items-baseline gap-2">
              <div className="pk text-[18px] text-[color:var(--green)]" style={{ textShadow: "0 0 6px rgba(0,255,65,0.4)" }}>
                <NumberTicker value={state.winRate*100} format={v => v.toFixed(0)+"%"} />
              </div>
              <div className="pk text-[7px] text-[color:var(--subdim)] tracking-widest">WIN RATE</div>
            </div>
            <div className="mt-2 flex gap-1 h-2">
              <div className="flex-1 border border-[color:var(--border)] bg-[color:var(--panel)] overflow-hidden">
                <motion.div
                  className="h-full"
                  style={{ background: "var(--green)", boxShadow: "0 0 4px var(--green)" }}
                  animate={{ width: `${state.winRate*100}%` }}
                />
              </div>
              <div className="flex-1 border border-[color:var(--border)] bg-[color:var(--panel)] overflow-hidden">
                <motion.div
                  className="h-full ml-auto"
                  style={{ background: "var(--red)", boxShadow: "0 0 4px var(--red)" }}
                  animate={{ width: `${(1-state.winRate)*100}%` }}
                />
              </div>
            </div>
          </InteractiveCard></div>
          <div className="xl:col-span-2"><InteractiveCard
            title="RISK EXPOSURE"
            tooltip="Fraction of capital currently deployed"
            accent={state.riskExposure > 0.5 ? "#ff3333" : state.riskExposure > 0.25 ? "#ffff00" : "#00ff41"}
            expanded={
              <div className="space-y-1 mono">
                <div>Exposure: {(state.riskExposure*100).toFixed(1)}%</div>
                <div>Max per trade: 8% (config)</div>
              </div>
            }
          >
            <div className="pk text-[18px] text-[color:var(--orange)]" style={{ textShadow: "0 0 6px rgba(255,136,0,0.4)" }}>
              <NumberTicker value={state.riskExposure*100} format={v => v.toFixed(1)+"%"} />
            </div>
            <div className="mt-3 h-1.5 border border-[color:var(--border)] bg-[color:var(--panel)]">
              <motion.div
                className="h-full"
                style={{
                  background: state.riskExposure > 0.5 ? "var(--red)" : state.riskExposure > 0.25 ? "var(--yellow)" : "var(--green)",
                  boxShadow: "0 0 4px currentColor",
                }}
                animate={{ width: `${state.riskExposure*100}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </InteractiveCard></div>
        </section>

        {/* ── Charts ── */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-3 md:gap-4">
          <EquityCurve data={equitySeries} pnl={state.pnl} peak={state.peakBalance} />
          <InteractiveCard
            title="MODEL CONFIDENCE · ROLLING"
            tooltip="Live edge trajectory — tracks decay or acceleration"
            accent="#00ff41"
          >
            <ConfidenceGraph data={confSeries} />
          </InteractiveCard>
        </section>

        {/* ── Activity Log ── */}
        <ActivityLog activeAgent={active} />

        <footer
          className="pt-4 pk text-[7px] tracking-widest text-center"
          style={{
            color: "#00ff41",
            textShadow: "0 0 6px #00ff41, 0 0 12px rgba(0,255,65,0.5)",
          }}
        >
          POWERED BY SIX EMPIRES · ALL RIGHTS RESERVED · COPYRIGHT 2026
        </footer>
      </motion.div>
    </div>
  )
}

export default function App() {
  // AppProvider is now mounted at the root in main.jsx
  return <Dashboard />
}
