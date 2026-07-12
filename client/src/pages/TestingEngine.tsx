import { useState, useEffect, useRef } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
interface Agent {
  id: string;
  name: string;
  type: string;
  color: string;
  glow: string;
  wins: number;
  losses: number;
  profit: number;
  winRate: number;
  status: "active" | "halted" | "learning";
  lastSignal: string;
  confidence: number;
  coldWallet: number;
}

interface Trade {
  id: number;
  agent: string;
  agentColor: string;
  asset: string;
  direction: "SHORT";
  entry: number;
  pnl: number;
  status: "open" | "closed" | "secured";
  time: string;
  indicators: number;
}

// ─── Constants ────────────────────────────────────────────────────────────────
const ASSETS = ["XRP", "AVAX", "SOL", "BTC", "ETH"];
const INITIAL_AGENTS: Agent[] = [
  { id: "guru",    name: "TRADING GURU",  type: "Master Agent",    color: "#ff6a00", glow: "rgba(255,106,0,0.4)",   wins: 0, losses: 0, profit: 0, winRate: 0, status: "active",   lastSignal: "—", confidence: 0, coldWallet: 0 },
  { id: "alpha",   name: "AGENT ALPHA",   type: "Claude",          color: "#00f5ff", glow: "rgba(0,245,255,0.3)",   wins: 0, losses: 0, profit: 0, winRate: 0, status: "active",   lastSignal: "—", confidence: 0, coldWallet: 0 },
  { id: "beta",    name: "AGENT BETA",    type: "Claude",          color: "#bf00ff", glow: "rgba(191,0,255,0.3)",   wins: 0, losses: 0, profit: 0, winRate: 0, status: "active",   lastSignal: "—", confidence: 0, coldWallet: 0 },
  { id: "gamma",   name: "AGENT GAMMA",   type: "DeepSeek-Math",   color: "#00ff88", glow: "rgba(0,255,136,0.3)",   wins: 0, losses: 0, profit: 0, winRate: 0, status: "active",   lastSignal: "—", confidence: 0, coldWallet: 0 },
  { id: "delta",   name: "AGENT DELTA",   type: "Quant",           color: "#ffd700", glow: "rgba(255,215,0,0.3)",   wins: 0, losses: 0, profit: 0, winRate: 0, status: "active",   lastSignal: "—", confidence: 0, coldWallet: 0 },
];

const INDICATORS = ["Hurst 4H", "Hurst 15M", "FVG/Support", "W%R", "RSI", "CVD Div", "Order Book", "Netflow", "MVRV Z"];

function rand(min: number, max: number) { return Math.random() * (max - min) + min; }
function randInt(min: number, max: number) { return Math.floor(rand(min, max + 1)); }
function pick<T>(arr: T[]): T { return arr[randInt(0, arr.length - 1)]; }

// ─── Particle Canvas ──────────────────────────────────────────────────────────
function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    let raf: number;
    const resize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight; };
    resize();
    window.addEventListener("resize", resize);
    const particles = Array.from({ length: 60 }, () => ({
      x: Math.random() * canvas.width, y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.5 + 0.5,
      color: pick(["#00f5ff", "#bf00ff", "#00ff88", "#ff6a00", "#ffd700"]),
      alpha: Math.random() * 0.6 + 0.2,
    }));
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = canvas.width; if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height; if (p.y > canvas.height) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.color + Math.floor(p.alpha * 255).toString(16).padStart(2, "0");
        ctx.fill();
      });
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, []);
  return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />;
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function TestingEngine() {
  const [agents, setAgents] = useState<Agent[]>(INITIAL_AGENTS);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [tradeCounter, setTradeCounter] = useState(0);
  const [running, setRunning] = useState(true);
  const [uptime, setUptime] = useState(0);
  const [guruLearning, setGuruLearning] = useState(false);
  const [lang, setLang] = useState<"ENG" | "ARM" | "RUSS">("ENG");
  const tradeCounterRef = useRef(0);

  // ── Uptime clock ──
  useEffect(() => {
    const t = setInterval(() => setUptime(s => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // ── Simulation tick ──
  useEffect(() => {
    if (!running) return;
    const interval = setInterval(() => {
      setAgents(prev => prev.map(agent => {
        if (agent.status === "halted") return agent;
        const win = Math.random() > 0.38;
        const pnl = win ? rand(5, 180) : -rand(5, 60);
        const newProfit = agent.profit + pnl;
        const newWins = win ? agent.wins + 1 : agent.wins;
        const newLosses = !win ? agent.losses + 1 : agent.losses;
        const total = newWins + newLosses;
        const winRate = total > 0 ? (newWins / total) * 100 : 0;
        const newCold = newProfit >= 100 && agent.coldWallet < Math.floor(newProfit / 100) * 100
          ? Math.floor(newProfit / 100) * 100 : agent.coldWallet;
        const halted = newLosses > 0 && newLosses % 5 === 0 && !win;
        const confidence = Math.round(rand(55, 100));
        const asset = pick(ASSETS);
        const lastSignal = `SHORT ${asset} @ ${confidence}% conf`;

        // Guru self-learning trigger
        if (agent.id === "guru" && win && Math.random() > 0.7) setGuruLearning(true);

        // Emit a trade log entry
        tradeCounterRef.current += 1;
        const tradeId = tradeCounterRef.current;
        const indicatorCount = randInt(6, 9);
        const newTrade: Trade = {
          id: tradeId, agent: agent.name, agentColor: agent.color,
          asset, direction: "SHORT",
          entry: parseFloat(rand(0.5, 65000).toFixed(2)),
          pnl: parseFloat(pnl.toFixed(2)),
          status: newCold > agent.coldWallet ? "secured" : win ? "closed" : "open",
          time: new Date().toLocaleTimeString(),
          indicators: indicatorCount,
        };
        setTrades(prev => [newTrade, ...prev].slice(0, 40));
        setTradeCounter(c => c + 1);

        return {
          ...agent,
          wins: newWins, losses: newLosses, profit: parseFloat(newProfit.toFixed(2)),
          winRate: parseFloat(winRate.toFixed(1)),
          status: halted ? "halted" : agent.id === "guru" && guruLearning ? "learning" : "active",
          lastSignal, confidence, coldWallet: newCold,
        };
      }));

      // Reset guru learning flag after brief period
      setTimeout(() => setGuruLearning(false), 1200);
    }, 1800);
    return () => clearInterval(interval);
  }, [running, guruLearning]);

  const formatUptime = (s: number) => {
    const h = Math.floor(s / 3600).toString().padStart(2, "0");
    const m = Math.floor((s % 3600) / 60).toString().padStart(2, "0");
    const sec = (s % 60).toString().padStart(2, "0");
    return `${h}:${m}:${sec}`;
  };

  const sortedAgents = [...agents].sort((a, b) => b.profit - a.profit);

  const labels: Record<string, Record<string, string>> = {
    title: { ENG: "TESTING ENGINE ARENA", ARM: "ԹԵՍՏ ԱՐԵՆԱ", RUSS: "АРЕНА ТЕСТИРОВАНИЯ" },
    subtitle: { ENG: "24/7 Self-Learning · Paper Trading · Real Market Data", ARM: "24/7 Ինքնուսուցում · Թղթային Առևտուր", RUSS: "24/7 Самообучение · Бумажная Торговля" },
    leaderboard: { ENG: "LEADERBOARD", ARM: "ԱՌԱՋԱՏԱՐՆԵՐ", RUSS: "ТАБЛИЦА ЛИДЕРОВ" },
    tradelog: { ENG: "LIVE TRADE LOG", ARM: "ԿԵՆԴԱՆԻ ԳՐԱՆՑԱՄԱՏՅԱՆ", RUSS: "ЖУРНАЛ СДЕЛОК" },
    uptime: { ENG: "UPTIME", ARM: "ԺԱՄԱՆԱԿ", RUSS: "АПТАЙМ" },
    trades: { ENG: "TRADES", ARM: "ԳՈՐԾ.", RUSS: "СДЕЛКИ" },
    start: { ENG: "START", ARM: "ՍԿՍԵԼ", RUSS: "СТАРТ" },
    pause: { ENG: "PAUSE", ARM: "ԴԱԴԱՐ", RUSS: "ПАУЗА" },
    coldwallet: { ENG: "COLD WALLET SECURED", ARM: "ՑՈՒՐՏ ԴՐԱՄԱՊԱՆԱԿ", RUSS: "ХОЛОДНЫЙ КОШЕЛЁК" },
  };
  const t = (key: string) => labels[key]?.[lang] ?? key;

  return (
    <div className="relative min-h-screen overflow-hidden" style={{ background: "linear-gradient(135deg,#020408 0%,#050d18 40%,#08001a 100%)", fontFamily: "'JetBrains Mono',monospace" }}>
      <ParticleCanvas />

      {/* ── Scan line overlay ── */}
      <div className="pointer-events-none absolute inset-0 z-0" style={{ background: "repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,245,255,0.015) 2px,rgba(0,245,255,0.015) 4px)" }} />

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-6">

        {/* ── Header ── */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
          <div>
            <div className="text-xs tracking-widest mb-1" style={{ color: "rgba(0,245,255,0.5)" }}>★ TRADINGGURU.AI · ARENA ENGINE</div>
            <h1 className="text-2xl md:text-4xl font-bold tracking-widest" style={{ color: "#00f5ff", textShadow: "0 0 30px rgba(0,245,255,0.6), 0 0 60px rgba(0,245,255,0.2)" }}>
              {t("title")}
            </h1>
            <p className="text-xs mt-1 tracking-wider" style={{ color: "rgba(0,245,255,0.5)" }}>{t("subtitle")}</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Lang buttons */}
            {(["ENG", "ARM", "RUSS"] as const).map(l => (
              <button key={l} onClick={() => setLang(l)}
                className="px-3 py-1 text-xs tracking-widest border transition-all"
                style={{ borderColor: lang === l ? "#ffd700" : "rgba(255,215,0,0.3)", color: lang === l ? "#ffd700" : "rgba(255,215,0,0.5)", background: lang === l ? "rgba(255,215,0,0.1)" : "transparent", boxShadow: lang === l ? "0 0 12px rgba(255,215,0,0.3)" : "none" }}>
                {l}
              </button>
            ))}
            {/* Start / Pause */}
            <button onClick={() => setRunning(r => !r)}
              className="px-4 py-1.5 text-xs tracking-widest border font-bold transition-all"
              style={{ borderColor: running ? "#ff6a00" : "#00ff88", color: running ? "#ff6a00" : "#00ff88", background: running ? "rgba(255,106,0,0.1)" : "rgba(0,255,136,0.1)", boxShadow: running ? "0 0 14px rgba(255,106,0,0.4)" : "0 0 14px rgba(0,255,136,0.4)" }}>
              {running ? `⏸ ${t("pause")}` : `▶ ${t("start")}`}
            </button>
          </div>
        </div>

        {/* ── Status Bar ── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {[
            { label: t("uptime"), value: formatUptime(uptime), color: "#00f5ff" },
            { label: t("trades"), value: tradeCounter.toString(), color: "#00ff88" },
            { label: "ASSETS", value: ASSETS.join(" · "), color: "#ffd700" },
            { label: "MODE", value: "SPOT · SHORT ONLY", color: "#bf00ff" },
          ].map(s => (
            <div key={s.label} className="border px-4 py-3" style={{ borderColor: `${s.color}33`, background: `${s.color}08` }}>
              <div className="text-xs tracking-widest mb-1" style={{ color: `${s.color}80` }}>{s.label}</div>
              <div className="text-sm font-bold tracking-wider truncate" style={{ color: s.color, textShadow: `0 0 10px ${s.color}60` }}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* ── Guru Learning Banner ── */}
        {guruLearning && (
          <div className="mb-6 border px-5 py-3 text-sm font-bold tracking-widest text-center animate-pulse"
            style={{ borderColor: "#ff6a00", color: "#ff6a00", background: "rgba(255,106,0,0.08)", boxShadow: "0 0 30px rgba(255,106,0,0.3)" }}>
            ★ TRADING GURU IS EXTRACTING WINNING PATTERNS FROM PEER AGENTS · SELF-UPGRADING IN PROGRESS ★
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

          {/* ── Leaderboard ── */}
          <div className="xl:col-span-2">
            <div className="border mb-1" style={{ borderColor: "rgba(0,245,255,0.2)", background: "rgba(0,0,0,0.6)" }}>
              <div className="px-5 py-3 border-b flex items-center justify-between" style={{ borderColor: "rgba(0,245,255,0.15)" }}>
                <span className="text-sm font-bold tracking-widest" style={{ color: "#00f5ff" }}>🏆 {t("leaderboard")}</span>
                <span className="text-xs tracking-widest" style={{ color: "rgba(0,245,255,0.4)" }}>LIVE · PAPER TRADING</span>
              </div>

              {/* Header row */}
              <div className="grid grid-cols-7 px-5 py-2 text-xs tracking-widest" style={{ color: "rgba(255,255,255,0.3)" }}>
                <span className="col-span-2">AGENT</span>
                <span className="text-right">PROFIT</span>
                <span className="text-right">WIN%</span>
                <span className="text-right">W/L</span>
                <span className="text-right">COLD $</span>
                <span className="text-right">STATUS</span>
              </div>

              {sortedAgents.map((agent, i) => (
                <div key={agent.id}
                  className="grid grid-cols-7 px-5 py-3 border-t items-center transition-all"
                  style={{ borderColor: "rgba(255,255,255,0.05)", background: i === 0 ? `${agent.color}08` : "transparent" }}>

                  {/* Rank + Name */}
                  <div className="col-span-2 flex items-center gap-3">
                    <span className="text-lg font-bold w-6 text-center" style={{ color: i === 0 ? "#ffd700" : i === 1 ? "#c0c0c0" : i === 2 ? "#cd7f32" : "rgba(255,255,255,0.3)" }}>
                      {i === 0 ? "★" : i + 1}
                    </span>
                    <div>
                      <div className="text-xs font-bold tracking-wider" style={{ color: agent.color, textShadow: `0 0 8px ${agent.glow}` }}>{agent.name}</div>
                      <div className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>{agent.type}</div>
                    </div>
                  </div>

                  {/* Profit */}
                  <div className="text-right text-sm font-bold" style={{ color: agent.profit >= 0 ? "#00ff88" : "#ff4444" }}>
                    {agent.profit >= 0 ? "+" : ""}${agent.profit.toFixed(0)}
                  </div>

                  {/* Win Rate */}
                  <div className="text-right">
                    <div className="text-xs font-bold" style={{ color: agent.winRate >= 60 ? "#00ff88" : agent.winRate >= 45 ? "#ffd700" : "#ff4444" }}>
                      {agent.winRate.toFixed(0)}%
                    </div>
                    <div className="w-full mt-1 h-1 rounded" style={{ background: "rgba(255,255,255,0.1)" }}>
                      <div className="h-1 rounded transition-all" style={{ width: `${agent.winRate}%`, background: agent.winRate >= 60 ? "#00ff88" : "#ffd700" }} />
                    </div>
                  </div>

                  {/* W/L */}
                  <div className="text-right text-xs" style={{ color: "rgba(255,255,255,0.6)" }}>
                    <span style={{ color: "#00ff88" }}>{agent.wins}</span>/<span style={{ color: "#ff4444" }}>{agent.losses}</span>
                  </div>

                  {/* Cold Wallet */}
                  <div className="text-right text-xs font-bold" style={{ color: "#ffd700" }}>
                    ${agent.coldWallet}
                  </div>

                  {/* Status */}
                  <div className="text-right">
                    <span className="text-xs px-2 py-0.5 tracking-widest"
                      style={{
                        color: agent.status === "active" ? "#00ff88" : agent.status === "halted" ? "#ff4444" : "#ff6a00",
                        border: `1px solid ${agent.status === "active" ? "#00ff8844" : agent.status === "halted" ? "#ff444444" : "#ff6a0044"}`,
                        background: agent.status === "active" ? "rgba(0,255,136,0.08)" : agent.status === "halted" ? "rgba(255,68,68,0.08)" : "rgba(255,106,0,0.08)",
                      }}>
                      {agent.status === "active" ? "● LIVE" : agent.status === "halted" ? "■ HALT" : "◈ LEARN"}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* ── Agent Signal Cards ── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
              {agents.map(agent => (
                <div key={agent.id} className="border p-4 transition-all"
                  style={{ borderColor: `${agent.color}33`, background: `${agent.color}06`, boxShadow: agent.status === "active" ? `0 0 15px ${agent.glow}` : "none" }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold tracking-widest" style={{ color: agent.color }}>{agent.name}</span>
                    <span className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>{agent.type}</span>
                  </div>
                  <div className="text-xs mb-2" style={{ color: "rgba(255,255,255,0.5)" }}>{agent.lastSignal}</div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>CONF</span>
                    <div className="flex-1 h-1.5 rounded" style={{ background: "rgba(255,255,255,0.1)" }}>
                      <div className="h-1.5 rounded transition-all" style={{ width: `${agent.confidence}%`, background: agent.color, boxShadow: `0 0 6px ${agent.color}` }} />
                    </div>
                    <span className="text-xs font-bold" style={{ color: agent.color }}>{agent.confidence}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Right Panel ── */}
          <div className="flex flex-col gap-4">

            {/* Cold Wallet Summary */}
            <div className="border p-4" style={{ borderColor: "rgba(255,215,0,0.3)", background: "rgba(255,215,0,0.04)" }}>
              <div className="text-xs font-bold tracking-widest mb-3" style={{ color: "#ffd700" }}>🔒 {t("coldwallet")}</div>
              {agents.map(agent => (
                <div key={agent.id} className="flex items-center justify-between py-1.5 border-b" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                  <span className="text-xs" style={{ color: agent.color }}>{agent.name}</span>
                  <span className="text-xs font-bold" style={{ color: "#ffd700" }}>${agent.coldWallet}</span>
                </div>
              ))}
              <div className="flex items-center justify-between pt-2 mt-1">
                <span className="text-xs tracking-widest" style={{ color: "rgba(255,215,0,0.6)" }}>TOTAL SECURED</span>
                <span className="text-sm font-bold" style={{ color: "#ffd700", textShadow: "0 0 10px rgba(255,215,0,0.5)" }}>
                  ${agents.reduce((s, a) => s + a.coldWallet, 0)}
                </span>
              </div>
            </div>

            {/* Live Trade Log */}
            <div className="border flex-1" style={{ borderColor: "rgba(0,255,136,0.2)", background: "rgba(0,0,0,0.6)" }}>
              <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: "rgba(0,255,136,0.15)" }}>
                <span className="text-xs font-bold tracking-widest" style={{ color: "#00ff88" }}>⚡ {t("tradelog")}</span>
                <span className="text-xs animate-pulse" style={{ color: "rgba(0,255,136,0.5)" }}>● STREAMING</span>
              </div>
              <div className="overflow-y-auto" style={{ maxHeight: "380px" }}>
                {trades.length === 0 && (
                  <div className="text-center py-8 text-xs tracking-widest" style={{ color: "rgba(255,255,255,0.2)" }}>WAITING FOR SIGNALS…</div>
                )}
                {trades.map(trade => (
                  <div key={trade.id} className="px-4 py-2.5 border-b flex flex-col gap-1 transition-all"
                    style={{ borderColor: "rgba(255,255,255,0.04)", background: trade.status === "secured" ? "rgba(255,215,0,0.04)" : "transparent" }}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold" style={{ color: trade.agentColor }}>{trade.agent}</span>
                      <span className="text-xs" style={{ color: trade.pnl >= 0 ? "#00ff88" : "#ff4444" }}>
                        {trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
                        SHORT {trade.asset} · {trade.indicators}/9 ✓
                      </span>
                      <span className="text-xs" style={{
                        color: trade.status === "secured" ? "#ffd700" : trade.status === "closed" ? "#00ff88" : "rgba(255,255,255,0.3)"
                      }}>
                        {trade.status === "secured" ? "🔒 SECURED" : trade.status === "closed" ? "✓ CLOSED" : "○ OPEN"}
                      </span>
                    </div>
                    <div className="text-xs" style={{ color: "rgba(255,255,255,0.2)" }}>{trade.time}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Checklist Reference */}
            <div className="border p-4" style={{ borderColor: "rgba(191,0,255,0.3)", background: "rgba(191,0,255,0.04)" }}>
              <div className="text-xs font-bold tracking-widest mb-3" style={{ color: "#bf00ff" }}>◈ GODS LEVEL CHECKLIST</div>
              <div className="grid grid-cols-1 gap-1">
                {INDICATORS.map((ind, i) => (
                  <div key={ind} className="flex items-center gap-2">
                    <span className="text-xs" style={{ color: i < 7 ? "#00ff88" : "rgba(255,255,255,0.3)" }}>{i < 7 ? "✓" : "○"}</span>
                    <span className="text-xs" style={{ color: i < 7 ? "rgba(255,255,255,0.7)" : "rgba(255,255,255,0.3)" }}>{ind}</span>
                  </div>
                ))}
              </div>
              <div className="mt-3 pt-3 border-t text-xs" style={{ borderColor: "rgba(191,0,255,0.2)", color: "rgba(191,0,255,0.7)" }}>
                POSITION = RISK ÷ STOP% × 0.25 Kelly
              </div>
            </div>
          </div>
        </div>

        {/* ── Footer ── */}
        <div className="mt-8 pt-4 border-t flex flex-col md:flex-row items-center justify-between gap-2 text-xs tracking-widest" style={{ borderColor: "rgba(0,245,255,0.1)", color: "rgba(255,255,255,0.2)" }}>
          <span>TRADINGGURU.AI · TESTING ENGINE v1.0 · PAPER TRADING MODE</span>
          <span>ASSETS: XRP · AVAX · SOL · BTC · ETH · SPOT · SHORT ONLY</span>
          <span style={{ color: "rgba(0,255,136,0.4)" }}>● 24/7 SELF-LEARNING ACTIVE</span>
        </div>
      </div>
    </div>
  );
}
