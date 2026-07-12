import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { audio } from "../ui/audio_engine.js"
import { AGENTS } from "../components/AgentSprites.jsx"
import ActionModal, { AmountInput, ConfirmButton } from "../components/ActionModal.jsx"
import WalletConnectModal, { getConnectedWallet } from "../components/WalletConnectModal.jsx"
import BetModal, { getBets } from "../components/BetModal.jsx"
import { getExchanges } from "../components/ExchangeConnectModal.jsx"
import LiveBotsPanel from "../components/LiveBotsPanel.jsx"
import KillSwitch from "../components/KillSwitch.jsx"
import L99StatusPanel from "../components/L99StatusPanel.jsx"

// Mock user profile
const USER = {
  handle:    "TRADER_7",
  level:     12,
  xp:        4280,
  xpForNext: 5000,
  since:     "2026-01-14",
  rank:      247,
  favAgent:  "alpha",
  balance:   12480.64,
  deposited: 10000,
  wins:      94,
  losses:    51,
  pnl:       2480.64,
}

// Mock trade history
const TRADES = [
  { id: 1, pair: "BTC/USDT",  side: "BUY", size: 240, pnl:  +18.40, agent: "alpha",    ts: "19:42:11" },
  { id: 2, pair: "ETH/USDT",  side: "BUY", size: 180, pnl:  +12.10, agent: "executor", ts: "19:40:03" },
  { id: 3, pair: "SOL/USDT",  side: "BUY", size: 160, pnl:   -6.20, agent: "skeptic",  ts: "19:37:28" },
  { id: 4, pair: "BNB/USDT",  side: "BUY", size: 220, pnl:  +32.80, agent: "hunter",   ts: "19:34:51" },
  { id: 5, pair: "BTC/USDT",  side: "BUY", size: 260, pnl:  -14.90, agent: "alpha",    ts: "19:30:02" },
  { id: 6, pair: "AVAX/USDT", side: "BUY", size: 140, pnl:   +9.35, agent: "regime",   ts: "19:26:41" },
  { id: 7, pair: "LINK/USDT", side: "BUY", size: 180, pnl:  +22.60, agent: "champion", ts: "19:22:18" },
  { id: 8, pair: "XRP/USDT",  side: "BUY", size: 200, pnl:   -8.50, agent: "risk",     ts: "19:18:49" },
]

function Stat({ label, value, color = "#00ff41", sub }) {
  return (
    <div className="qwr-panel p-4">
      <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mb-2">{label}</div>
      <div
        className="pk text-xl md:text-2xl"
        style={{ color, textShadow: `0 0 10px ${color}80` }}
      >
        {value}
      </div>
      {sub && <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mt-2">{sub}</div>}
    </div>
  )
}

export default function UserDashboard() {
  const [now, setNow] = useState(new Date())
  const [action, setAction] = useState(null)   // "deposit" | "withdraw" | "copy" | "edit" | "wallet"
  const [amount, setAmount] = useState("1000")
  const [wallet, setWallet] = useState(() => getConnectedWallet())
  const [flash, setFlash] = useState(null)
  const [bets, setBets] = useState(() => getBets())
  const [exchanges, setExchanges] = useState(() => getExchanges())
  const [betOpen, setBetOpen] = useState(false)

  useEffect(() => { const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t) }, [])
  useEffect(() => {
    const onW = (e) => setWallet(e.detail)
    const onB = (e) => setBets(e.detail)
    const onE = (e) => setExchanges(e.detail)
    window.addEventListener("qwr:wallet", onW)
    window.addEventListener("qwr:bets", onB)
    window.addEventListener("qwr:exchanges", onE)
    return () => {
      window.removeEventListener("qwr:wallet", onW)
      window.removeEventListener("qwr:bets", onB)
      window.removeEventListener("qwr:exchanges", onE)
    }
  }, [])

  const confirmAction = (kind) => {
    audio.triumph?.()
    setFlash({ kind, amount })
    setAction(null)
    setTimeout(() => setFlash(null), 3500)
  }

  const favAgent = AGENTS.find(a => a.id === USER.favAgent)
  const xpPct = (USER.xp / USER.xpForNext) * 100
  const wr = Math.round((USER.wins / (USER.wins + USER.losses)) * 100)

  return (
    <div className="relative min-h-screen qwr-crt">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 0.61, 0.36, 1] }}
        className="relative z-10 max-w-[1400px] mx-auto px-4 md:px-8 pt-20 pb-16 space-y-6"
      >
        {/* ── Profile header ── */}
        <section className="qwr-panel p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            {/* Avatar (pixel) */}
            <div
              className="w-16 h-16 flex items-center justify-center"
              style={{
                background: `linear-gradient(135deg, ${favAgent.color}33, transparent)`,
                border: `1px solid ${favAgent.color}`,
                boxShadow: `0 0 16px ${favAgent.color}66`,
              }}
            >
              <favAgent.Sprite size={48} color={favAgent.color} />
            </div>
            <div>
              <div
                className="pk text-sm tracking-widest"
                style={{ color: "#00ff41", textShadow: "0 0 8px rgba(0,255,65,0.6)" }}
              >
                ◆ {USER.handle}
              </div>
              <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] mt-1">
                MEMBER SINCE {USER.since} · GLOBAL RANK #{USER.rank}
              </div>
            </div>
          </div>

          {/* Level + XP bar */}
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)]">LVL</div>
              <div
                className="pk text-2xl"
                style={{ color: "#00ffff", textShadow: "0 0 10px rgba(0,255,255,0.6)" }}
              >
                {USER.level}
              </div>
            </div>
            <div className="w-40">
              <div className="flex items-center justify-between pk text-[7px] tracking-widest text-[color:var(--subdim)] mb-1">
                <span>XP</span>
                <span>{USER.xp} / {USER.xpForNext}</span>
              </div>
              <div className="h-2 border border-[color:var(--border)] bg-[color:var(--panel)]">
                <motion.div
                  className="h-full"
                  style={{
                    background: "linear-gradient(90deg, #00ffff, #00ff41)",
                    boxShadow: "0 0 8px rgba(0,255,255,0.7)",
                  }}
                  initial={{ width: 0 }}
                  animate={{ width: `${xpPct}%` }}
                  transition={{ duration: 1.2, ease: "easeOut" }}
                />
              </div>
            </div>
          </div>
        </section>

        {/* ── L99 Champion-mode system status ── */}
        <L99StatusPanel />

        {/* ── Live bot status (legacy spot Vote bots) ── */}
        <LiveBotsPanel />

        {/* ── Emergency controls ── */}
        <KillSwitch />

        {/* ── Key stats (mock TRADER_7 profile) ── */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Stat label="BALANCE"   value={"$" + USER.balance.toFixed(2)} color="#00ff41" sub="USDT — live" />
          <Stat label="NET PnL"   value={(USER.pnl >= 0 ? "+" : "") + "$" + USER.pnl.toFixed(2)} color={USER.pnl >= 0 ? "#00ff41" : "#ff3333"} sub={`${((USER.pnl / USER.deposited)*100).toFixed(2)}% ROI`} />
          <Stat label="WIN RATE"  value={wr + "%"} color="#ffff00" sub={`${USER.wins}W · ${USER.losses}L`} />
          <Stat label="TOTAL TRADES" value={USER.wins + USER.losses} color="#00ffff" />
        </section>

        {/* ── Balance chart + Deposit / Withdraw ── */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 qwr-panel p-5">
            <div
              className="pk text-[10px] tracking-widest mb-3"
              style={{ color: "#00ff41", textShadow: "0 0 8px rgba(0,255,65,0.5)" }}
            >
              ◆ BALANCE HISTORY · 7D
            </div>
            <svg viewBox="0 0 200 60" preserveAspectRatio="none" className="w-full h-36">
              <defs>
                <linearGradient id="bFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%"   stopColor="#00ff41" stopOpacity="0.5" />
                  <stop offset="100%" stopColor="#00ff41" stopOpacity="0"   />
                </linearGradient>
              </defs>
              <polyline
                fill="url(#bFill)"
                stroke="none"
                points="0,50 20,48 40,45 60,40 80,44 100,30 120,34 140,22 160,18 180,14 200,10 200,60 0,60"
              />
              <polyline
                fill="none"
                stroke="#00ff41"
                strokeWidth="1.5"
                points="0,50 20,48 40,45 60,40 80,44 100,30 120,34 140,22 160,18 180,14 200,10"
                style={{ filter: "drop-shadow(0 0 4px #00ff41)" }}
              />
            </svg>
            <div className="mt-2 pk text-[7px] tracking-widest text-[color:var(--subdim)] flex justify-between">
              <span>DAY -7</span><span>-5</span><span>-3</span><span>-1</span><span>TODAY</span>
            </div>
          </div>

          {/* Quick actions */}
          <div className="qwr-panel p-5 space-y-3">
            <div
              className="pk text-[10px] tracking-widest mb-3"
              style={{ color: "#ffff00", textShadow: "0 0 8px rgba(255,255,0,0.5)" }}
            >
              ★ QUICK ACTIONS
            </div>
            {[
              { id: "deposit",  label: "DEPOSIT USDT",   color: "#00ff41" },
              { id: "withdraw", label: "WITHDRAW FUNDS", color: "#00ffff" },
              { id: "copy",     label: "COPY TRADER",    color: "#ffff00" },
              { id: "edit",     label: "EDIT AGENT CFG", color: "#cc44ff" },
            ].map(a => (
              <motion.button
                key={a.id}
                whileHover={{ scale: 1.02, x: 2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => { audio.click?.(); setAction(a.id) }}
                className="w-full pk text-[10px] tracking-widest px-4 py-3 border text-left"
                style={{
                  color: a.color,
                  borderColor: a.color + "55",
                  background: a.color + "10",
                }}
              >
                ► {a.label}
              </motion.button>
            ))}
          </div>
        </section>

        {/* ── Recent trades ── */}
        <section className="qwr-panel p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div
              className="pk text-[10px] tracking-widest"
              style={{ color: "#00ff41", textShadow: "0 0 8px rgba(0,255,65,0.5)" }}
            >
              ► RECENT TRADES
            </div>
            <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)]">
              {now.toTimeString().slice(0,8)} UTC
            </div>
          </div>

          <div className="grid grid-cols-12 gap-2 pk text-[8px] tracking-widest text-[color:var(--subdim)] border-b border-[color:var(--border)] pb-2">
            <div className="col-span-2">TIME</div>
            <div className="col-span-2">PAIR</div>
            <div className="col-span-1">SIDE</div>
            <div className="col-span-2 text-right">SIZE</div>
            <div className="col-span-2 text-right">PnL</div>
            <div className="col-span-3">AGENT</div>
          </div>
          {TRADES.map((t, i) => {
            const agent = AGENTS.find(a => a.id === t.agent)
            const up = t.pnl > 0
            return (
              <div
                key={t.id}
                className="grid grid-cols-12 gap-2 items-center py-2 border-b border-[color:var(--border)]/50 mono text-[11px]"
              >
                <div className="col-span-2 text-[color:var(--subdim)]">{t.ts}</div>
                <div className="col-span-2 text-[color:var(--text)]">{t.pair}</div>
                <div className="col-span-1">
                  <span
                    className="pk text-[8px] px-1 py-0.5 border"
                    style={{
                      color: "#00ff41",
                      borderColor: "#00ff41",
                      background: "rgba(0,255,65,0.12)",
                    }}
                  >
                    {t.side}
                  </span>
                </div>
                <div className="col-span-2 text-right text-[color:var(--text)]">${t.size}</div>
                <div
                  className="col-span-2 text-right"
                  style={{
                    color: up ? "#00ff41" : "#ff3333",
                    textShadow: `0 0 4px ${up ? "rgba(0,255,65,0.4)" : "rgba(255,51,51,0.4)"}`,
                  }}
                >
                  {up ? "+" : ""}${t.pnl.toFixed(2)}
                </div>
                <div className="col-span-3 flex items-center gap-2">
                  <div
                    className="w-6 h-6 flex items-center justify-center"
                    style={{
                      background: `linear-gradient(135deg, ${agent.color}22, transparent)`,
                      border: `1px solid ${agent.color}55`,
                    }}
                  >
                    <agent.Sprite size={20} color={agent.color} />
                  </div>
                  <span className="pk text-[8px]" style={{ color: agent.color }}>
                    {agent.name}
                  </span>
                </div>
              </div>
            )
          })}
        </section>

        {/* ── MY BETS + EXCHANGES ── */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Active bets */}
          <div className="qwr-panel p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div
                className="pk text-[10px] tracking-widest"
                style={{ color: "#ffff00", textShadow: "0 0 8px rgba(255,255,0,0.5)" }}
              >★ MY BETS ({bets.length})</div>
              <motion.button
                whileHover={{ scale: 1.04 }}
                onClick={() => { audio.click?.(); setBetOpen(true) }}
                className="pk text-[9px] tracking-widest px-3 py-1 border"
                style={{
                  color: "#ffff00",
                  borderColor: "#ffff00",
                  background: "rgba(255,255,0,0.1)",
                }}
              >+ NEW BET</motion.button>
            </div>
            {bets.length === 0 ? (
              <div className="mono text-[11px] text-[color:var(--subdim)] text-center py-4">
                No active bets. Pick an agent and back them to reach $1M.
              </div>
            ) : (
              <div className="space-y-2">
                {bets.slice(-5).reverse().map(b => {
                  const agent = AGENTS.find(a => a.id === b.agentId)
                  return (
                    <div key={b.id}
                         className="flex items-center gap-3 p-2 border"
                         style={{ borderColor: b.color + "55", background: b.color + "08" }}>
                      <div className="w-8 h-8 flex items-center justify-center"
                           style={{ border: `1px solid ${b.color}`, background: b.color + "22" }}>
                        <agent.Sprite size={22} color={b.color} />
                      </div>
                      <div className="flex-1">
                        <div className="pk text-[10px]" style={{ color: b.color }}>{b.agentName}</div>
                        <div className="mono text-[9px] text-[color:var(--subdim)]">
                          ${b.stake} @ {b.odds.toFixed(2)}x
                        </div>
                      </div>
                      <div className="pk text-[10px]" style={{ color: "#00ff41" }}>
                        → ${b.payout.toFixed(2)}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Connected exchanges */}
          <div className="qwr-panel p-5 space-y-3">
            <div
              className="pk text-[10px] tracking-widest mb-2"
              style={{ color: "#00ffff", textShadow: "0 0 8px rgba(0,255,255,0.5)" }}
            >◈ CONNECTED EXCHANGES ({exchanges.length})</div>
            {exchanges.length === 0 ? (
              <div className="mono text-[11px] text-[color:var(--subdim)] text-center py-4">
                No exchanges connected. Use ◈ EXCHANGES in the nav bar to link your API keys.
              </div>
            ) : (
              <div className="space-y-2">
                {exchanges.map(e => (
                  <div key={e.id}
                       className="flex items-center gap-3 p-2 border"
                       style={{ borderColor: e.color + "55", background: e.color + "08" }}>
                    <div style={{ fontSize: 22 }}>{e.icon}</div>
                    <div className="flex-1">
                      <div className="pk text-[10px]" style={{ color: e.color }}>{e.name}</div>
                      <div className="mono text-[9px] text-[color:var(--subdim)]">API: {e.keyMasked}</div>
                    </div>
                    <div className="pk text-[10px]" style={{ color: "#00ff41" }}>
                      ${e.balance.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* ── Enter Arena CTA ── */}
        <section className="qwr-panel p-6 text-center space-y-4">
          <div
            className="pk text-lg md:text-xl text-[color:var(--green)]"
            style={{ textShadow: "0 0 14px rgba(0,255,65,0.7)" }}
          >
            YOUR AGENTS ARE LIVE
          </div>
          <div className="pk text-[9px] tracking-widest text-[color:var(--subdim)]">
            WATCH THEM RACE IN REAL-TIME
          </div>
          <Link to="/arena" onClick={() => audio.click?.()}>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="pk text-sm px-8 py-4 border tracking-widest"
              style={{
                color: "#00ff41",
                borderColor: "#00ff41",
                background: "rgba(0,255,65,0.1)",
                boxShadow: "0 0 20px rgba(0,255,65,0.4)",
                textShadow: "0 0 8px rgba(0,255,65,0.8)",
              }}
            >
              ► ENTER ARENA
            </motion.button>
          </Link>
        </section>

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

      {/* ── DEPOSIT ── */}
      <ActionModal open={action==="deposit"} onClose={() => setAction(null)} title="DEPOSIT USDT" color="#00ff41">
        {!wallet && (
          <div className="mono text-[11px] text-[color:var(--yellow)] mb-3">
            ⚠ Connect a wallet first to deposit funds.
          </div>
        )}
        <AmountInput label="AMOUNT TO DEPOSIT" value={amount} setValue={setAmount} color="#00ff41" />
        <div className="mono text-[10px] text-[color:var(--subdim)] mt-3 leading-relaxed">
          ► Funds go to your trading balance<br/>
          ► Instant confirmation on BSC / ETH / Polygon<br/>
          ► No deposit fees — network gas applies
        </div>
        <ConfirmButton
          label={wallet ? `CONFIRM DEPOSIT OF $${amount}` : "CONNECT WALLET FIRST"}
          color="#00ff41"
          onClick={() => confirmAction("deposit")}
          disabled={!wallet || !amount || +amount < 10}
        />
      </ActionModal>

      {/* ── WITHDRAW ── */}
      <ActionModal open={action==="withdraw"} onClose={() => setAction(null)} title="WITHDRAW FUNDS" color="#00ffff">
        {!wallet && (
          <div className="mono text-[11px] text-[color:var(--yellow)] mb-3">
            ⚠ Connect a wallet first to receive funds.
          </div>
        )}
        <AmountInput label="AMOUNT TO WITHDRAW" value={amount} setValue={setAmount} max={USER.balance} color="#00ffff" />
        <div className="mono text-[10px] text-[color:var(--subdim)] mt-3 leading-relaxed">
          ► Available balance: ${USER.balance.toFixed(2)} USDT<br/>
          ► Processing time: ~30 seconds<br/>
          ► Withdrawal fee: 0.5 USDT (network gas)
        </div>
        <ConfirmButton
          label={wallet ? `CONFIRM WITHDRAW OF $${amount}` : "CONNECT WALLET FIRST"}
          color="#00ffff"
          onClick={() => confirmAction("withdraw")}
          disabled={!wallet || !amount || +amount < 10 || +amount > USER.balance}
        />
      </ActionModal>

      {/* ── COPY TRADER ── */}
      <ActionModal open={action==="copy"} onClose={() => setAction(null)} title="COPY TOP TRADER" color="#ffff00">
        <div className="mono text-[11px] text-[color:var(--subdim)] mb-3">
          Mirror another agent's trades with your balance. Auto-sized to your capital.
        </div>
        <div className="space-y-2">
          {AGENTS.slice(0, 4).map((a, i) => {
            const roi = [42.8, 38.2, 31.6, 28.4][i]
            return (
              <motion.button
                key={a.id}
                whileHover={{ x: 3 }}
                onClick={() => { audio.click?.(); confirmAction("copy-" + a.id) }}
                className="w-full flex items-center gap-3 p-3 border text-left"
                style={{ borderColor: a.color + "55", background: a.color + "08" }}
              >
                <div className="w-10 h-10 flex items-center justify-center"
                     style={{ border: `1px solid ${a.color}`, background: a.color + "22" }}>
                  <a.Sprite size={28} color={a.color} />
                </div>
                <div className="flex-1">
                  <div className="pk text-[11px]" style={{ color: a.color }}>{a.name}</div>
                  <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mt-1">{a.role}</div>
                </div>
                <div className="pk text-[11px]" style={{ color: "#00ff41", textShadow: "0 0 4px rgba(0,255,65,0.5)" }}>
                  +{roi}%
                </div>
              </motion.button>
            )
          })}
        </div>
      </ActionModal>

      {/* ── EDIT AGENT CFG ── */}
      <ActionModal open={action==="edit"} onClose={() => setAction(null)} title="EDIT AGENT CONFIG" color="#cc44ff">
        <div className="space-y-3 mono text-[11px]">
          {[
            { label: "MAX POSITION SIZE",    value: "8%",     hint: "per trade" },
            { label: "MIN CONSENSUS VOTES",  value: "3 / 8",  hint: "to enter" },
            { label: "DAILY LOSS LIMIT",     value: "3.5%",   hint: "halt threshold" },
            { label: "PAIR SWITCH TRIGGER",  value: "-1.5%",  hint: "cumulative PnL" },
            { label: "MAX HOLD DURATION",    value: "15 min", hint: "time-stop" },
          ].map(row => (
            <div key={row.label} className="flex items-center justify-between py-2 border-b border-[color:var(--border)]/60">
              <div>
                <div className="pk text-[9px] tracking-widest text-[color:var(--text)]">{row.label}</div>
                <div className="pk text-[7px] tracking-widest text-[color:var(--subdim)] mt-1">{row.hint}</div>
              </div>
              <input
                defaultValue={row.value}
                className="w-24 bg-transparent border px-2 py-1 pk text-[10px] text-center"
                style={{ borderColor: "var(--border)", color: "#cc44ff" }}
              />
            </div>
          ))}
        </div>
        <ConfirmButton label="SAVE CONFIG" color="#cc44ff" onClick={() => confirmAction("edit")} />
      </ActionModal>

      <BetModal open={betOpen} onClose={() => setBetOpen(false)} />

      {/* Flash toast */}
      {flash && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0 }}
          className="fixed bottom-6 left-1/2 -translate-x-1/2 qwr-panel px-5 py-3 z-[140]"
          style={{ boxShadow: "0 0 20px rgba(0,255,65,0.5)" }}
        >
          <div className="pk text-[10px] tracking-widest text-[color:var(--green)]">
            ✓ {flash.kind.toUpperCase()} · ${flash.amount} · CONFIRMED
          </div>
        </motion.div>
      )}
    </div>
  )
}
