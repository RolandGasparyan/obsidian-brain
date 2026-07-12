import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { audio } from "../ui/audio_engine.js"

/**
 * Kill switch panel — lets the operator stop / start / restart all
 * paper bots from the browser via /api/control/*.
 *
 * Security: the control endpoints require an X-Control-Token header
 * matching a secret stored on the VPS. We store it in localStorage
 * under `qwr.control.token.v1` — user pastes it once, then every
 * button click re-sends it. There is NO auth on the frontend itself
 * (anyone can open the page), the token is the single wall.
 */

const TOKEN_KEY = "qwr.control.token.v1"

function loadToken() {
  try { return localStorage.getItem(TOKEN_KEY) || "" } catch { return "" }
}
function saveToken(t) {
  try { localStorage.setItem(TOKEN_KEY, t || "") } catch {}
}

async function callControl(action, token) {
  const r = await fetch(`/api/control/${action}`, {
    method: "POST",
    headers: { "X-Control-Token": token, "Content-Type": "application/json" },
  })
  const body = await r.json().catch(() => ({}))
  return { ok: r.ok, status: r.status, body }
}

export default function KillSwitch() {
  const [token, setToken] = useState(loadToken)
  const [busy, setBusy]   = useState(false)
  const [msg, setMsg]     = useState(null)   // { kind: "ok"|"err", text }
  const [confirm, setConfirm] = useState(false)
  const [tokenOpen, setTokenOpen] = useState(!loadToken())

  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 4500); return () => clearTimeout(t) } }, [msg])

  const run = async (action, needsConfirm = false) => {
    if (!token) { setTokenOpen(true); return }
    if (needsConfirm && !confirm) { setConfirm(action); return }
    setConfirm(false)
    setBusy(true)
    audio.click?.()
    try {
      const r = await callControl(action, token)
      if (r.ok)       setMsg({ kind: "ok",  text: `✅ ${action} — done` })
      else if (r.status === 401) setMsg({ kind: "err", text: "🔒 token rejected" })
      else            setMsg({ kind: "err", text: `❌ ${action} failed (${r.status})` })
    } catch (e) {
      setMsg({ kind: "err", text: `❌ ${e.message}` })
    } finally {
      setBusy(false)
    }
  }

  const saveAndClose = () => {
    saveToken(token.trim())
    setTokenOpen(false)
    setMsg({ kind: "ok", text: "🔑 token saved" })
  }

  return (
    <div
      className="qwr-panel p-4 md:p-5 space-y-3"
      style={{ borderColor: "rgba(255,85,119,0.45)", boxShadow: "0 0 14px rgba(255,85,119,0.25)" }}
    >
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div
          className="pk text-[10px] tracking-widest"
          style={{ color: "#ff5577", textShadow: "0 0 8px rgba(255,85,119,0.6)" }}
        >
          ⚠ KILL SWITCH
        </div>
        <button
          onClick={() => setTokenOpen(true)}
          className="pk text-[8px] tracking-widest text-[color:var(--subdim)] hover:text-white transition"
        >
          {token ? "🔑 token set ✓" : "🔑 set token"}
        </button>
      </div>

      <div className="pk text-[8px] tracking-widest text-[color:var(--subdim)] leading-relaxed">
        Emergency control for the 4 paper bots. Requires the VPS control
        token. Stop-All flattens positions via systemd, no real money at
        risk in Stage 1.
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <ActionBtn color="#ff5577" disabled={busy}
          onClick={() => run("stop-all", true)}>
          🛑 STOP ALL
        </ActionBtn>
        <ActionBtn color="#ffaa33" disabled={busy}
          onClick={() => run("restart-all", true)}>
          🔄 RESTART ALL
        </ActionBtn>
        <ActionBtn color="#00ff41" disabled={busy}
          onClick={() => run("start-all", false)}>
          ▶ START ALL
        </ActionBtn>
        <ActionBtn color="#00ffff" disabled={busy}
          onClick={async () => {
            if (!token) { setTokenOpen(true); return }
            setBusy(true)
            try {
              const r = await fetch("/api/control/status", {
                headers: { "X-Control-Token": token },
              })
              const j = await r.json()
              setMsg({ kind: "ok", text: `ℹ ${j.bots.map(b => `${b.pair.replace("_USDT","")}:${b.state}`).join("  ")}` })
            } catch (e) { setMsg({ kind: "err", text: e.message }) }
            finally     { setBusy(false) }
          }}>
          ℹ STATUS
        </ActionBtn>
      </div>

      <AnimatePresence>
        {msg && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="pk text-[9px] tracking-widest px-2 py-2 border"
            style={{
              color: msg.kind === "ok" ? "#00ff41" : "#ff5577",
              borderColor: (msg.kind === "ok" ? "#00ff41" : "#ff5577") + "55",
              background: (msg.kind === "ok" ? "#00ff41" : "#ff5577") + "10",
            }}
          >
            {msg.text}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Confirmation modal */}
      <AnimatePresence>
        {confirm && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[120] flex items-center justify-center p-4"
            style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}
            onClick={() => setConfirm(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }} animate={{ scale: 1 }} exit={{ scale: 0.9 }}
              onClick={(e) => e.stopPropagation()}
              className="qwr-panel p-6 max-w-md w-full space-y-4"
              style={{ borderColor: "#ff5577" }}
            >
              <div className="pk text-[12px] tracking-widest" style={{ color: "#ff5577" }}>
                ⚠ CONFIRM {confirm.toUpperCase()}
              </div>
              <div className="pk text-[9px] tracking-widest text-[color:var(--dim)] leading-relaxed">
                About to <span style={{ color: "#ff5577" }}>{confirm}</span> all 4 bots.
                Open positions will be closed at market.
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setConfirm(false)}
                  className="pk text-[9px] tracking-widest px-4 py-2 border border-[color:var(--border)] text-[color:var(--dim)]"
                >
                  CANCEL
                </button>
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.96 }}
                  onClick={() => { const act = confirm; setConfirm(true); run(act, false) }}
                  disabled={busy}
                  className="pk text-[9px] tracking-widest px-4 py-2 border"
                  style={{ color: "#ff5577", borderColor: "#ff5577", background: "#ff557722" }}
                >
                  CONFIRM
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Token setup modal */}
      <AnimatePresence>
        {tokenOpen && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[120] flex items-center justify-center p-4"
            style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}
            onClick={() => setTokenOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.9 }} animate={{ scale: 1 }} exit={{ scale: 0.9 }}
              onClick={(e) => e.stopPropagation()}
              className="qwr-panel p-6 max-w-lg w-full space-y-3"
              style={{ borderColor: "#ffaa33" }}
            >
              <div className="pk text-[11px] tracking-widest" style={{ color: "#ffaa33" }}>
                🔑 CONTROL TOKEN
              </div>
              <div className="pk text-[8px] tracking-widest text-[color:var(--dim)] leading-relaxed">
                Paste the token from the VPS (see{" "}
                <code className="text-[color:var(--green)]">/etc/trading-bot-control.token</code>).
                Saved locally in your browser.
              </div>
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="paste token…"
                className="w-full px-3 py-2 bg-black/50 border border-[color:var(--border)] text-white pk text-[9px] tracking-widest"
                autoFocus
              />
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setTokenOpen(false)}
                  className="pk text-[9px] tracking-widest px-4 py-2 border border-[color:var(--border)] text-[color:var(--dim)]"
                >
                  CANCEL
                </button>
                <motion.button
                  whileHover={{ scale: 1.04 }}
                  onClick={saveAndClose}
                  className="pk text-[9px] tracking-widest px-4 py-2 border"
                  style={{ color: "#00ff41", borderColor: "#00ff41", background: "#00ff4122" }}
                >
                  SAVE
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ActionBtn({ color, onClick, children, disabled }) {
  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.03 }}
      whileTap={{   scale: disabled ? 1 : 0.97 }}
      onClick={onClick}
      disabled={disabled}
      className="pk text-[9px] tracking-widest px-3 py-3 border transition"
      style={{
        color, borderColor: color + "88",
        background: color + "14",
        boxShadow: `0 0 8px ${color}44`,
        opacity: disabled ? 0.55 : 1,
        cursor: disabled ? "wait" : "pointer",
      }}
    >
      {children}
    </motion.button>
  )
}
