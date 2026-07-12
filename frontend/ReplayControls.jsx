/**
 * ReplayControls.jsx — playback + mode buttons (esports HUD style)
 *
 * 🛡 READ-ONLY UI · emits events only, no side-effects.
 */

import React from "react";

const REWIND_OPTIONS = [
  { label: "−1m",  seconds: 60 },
  { label: "−5m",  seconds: 300 },
  { label: "−1h",  seconds: 3600 },
  { label: "−24h", seconds: 86400 },
];

const RATE_OPTIONS = [1, 2, 4, 8];
const MODE_OPTIONS = [
  { id: "cinematic",      label: "🎬 CINEMATIC",       hint: "bold motion · large transitions" },
  { id: "tactical",       label: "📊 TACTICAL",        hint: "dense data · multi-panel" },
  { id: "minimal",        label: "⚡ MINIMAL",          hint: "scrubber + crowd only" },
  { id: "auto-highlight", label: "🌟 AUTO-HIGHLIGHT",  hint: "cycle boss moments" },
];

export default function ReplayControls({
  isLive,
  playRate,
  mode,
  onLiveToggle,
  onRateChange,
  onModeChange,
  onJumpRewind,
}) {
  const btn = {
    background: "rgba(245, 158, 11, 0.08)",
    border: "1px solid rgba(245, 158, 11, 0.35)",
    color: "#fbbf24",
    padding: "6px 12px",
    borderRadius: 6,
    fontSize: 11,
    letterSpacing: "0.1em",
    cursor: "pointer",
    fontFamily: "'JetBrains Mono', monospace",
    transition: "all 0.15s ease",
  };
  const btnActive = {
    ...btn,
    background: "linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)",
    color: "#000",
    boxShadow: "0 0 16px rgba(251, 191, 36, 0.6)",
    fontWeight: 700,
  };

  return (
    <div style={{
      display: "flex", flexWrap: "wrap",
      alignItems: "center", gap: 16,
      paddingTop: 4,
    }}>

      {/* Rewind buttons */}
      <div style={{ display: "flex", gap: 6 }}>
        {REWIND_OPTIONS.map(opt => (
          <button key={opt.seconds}
                  onClick={() => onJumpRewind(opt.seconds)}
                  style={btn}
                  title={`Rewind ${opt.label}`}>
            {opt.label}
          </button>
        ))}
      </div>

      <div style={{ width: 1, height: 24,
                     background: "rgba(245, 158, 11, 0.2)" }} />

      {/* Live toggle */}
      <button onClick={onLiveToggle}
              style={isLive ? btnActive : btn}>
        {isLive ? "● LIVE" : "○ HISTORICAL"}
      </button>

      {/* Playback rate (informational — playback is implicit via polling) */}
      <div style={{ display: "flex", gap: 4 }}>
        <span style={{ fontSize: 10, color: "#8a8478",
                        alignSelf: "center", marginRight: 4 }}>RATE</span>
        {RATE_OPTIONS.map(r => (
          <button key={r}
                  onClick={() => onRateChange(r)}
                  style={r === playRate ? btnActive : btn}>
            {r}×
          </button>
        ))}
      </div>

      <div style={{ width: 1, height: 24,
                     background: "rgba(245, 158, 11, 0.2)" }} />

      {/* Mode picker */}
      <div style={{ display: "flex", gap: 6 }}>
        {MODE_OPTIONS.map(m => (
          <button key={m.id}
                  onClick={() => onModeChange(m.id)}
                  title={m.hint}
                  style={m.id === mode ? btnActive : btn}>
            {m.label}
          </button>
        ))}
      </div>
    </div>
  );
}
