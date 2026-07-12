/**
 * ReplayEventFeed.jsx — rolling event feed sidebar with type-coded styling
 *
 * 🛡 READ-ONLY UI · renders /api/battle/replay-events-recent.json
 */

import React from "react";

const EVENT_STYLE = {
  AGENT_LEADER_CHANGE: { color: "#fbbf24", icon: "👑", label: "LEADER" },
  XP_JUMP:             { color: "#22c55e", icon: "⬆️",  label: "XP+" },
  XP_COLLAPSE:         { color: "#ef4444", icon: "⬇️",  label: "XP−" },
  REGIME_TRANSITION:   { color: "#06b6d4", icon: "🌀",  label: "REGIME" },
  VOLATILITY_STORM:    { color: "#a855f7", icon: "⚡",   label: "STORM" },
  CROWD_REACTION:      { color: "#ec4899", icon: "🎭",  label: "CROWD" },
  BOSS_EVENT:          { color: "#facc15", icon: "🐉",  label: "BOSS" },
  STREAK:              { color: "#f59e0b", icon: "🔥",  label: "STREAK" },
  CHAMPION_SWAP:       { color: "#fbbf24", icon: "🏆",  label: "CHAMPION" },
};

export default function ReplayEventFeed({
  events = [],
  cursorTs = null,
  highlightMoments = [],
}) {
  // If we have a cursor, fade events ahead of it
  const cursorActive = cursorTs !== null;
  const momentIds = new Set(highlightMoments.map(m => m.event_id));

  if (!events.length) {
    return (
      <div style={{
        background: "rgba(0,0,0,0.5)", borderRadius: 8,
        border: "1px solid rgba(245, 158, 11, 0.18)",
        padding: "20px 16px",
        color: "#5e5a52", fontSize: 11, letterSpacing: "0.18em",
        textAlign: "center",
      }}>⏳ no events yet…</div>
    );
  }

  return (
    <div style={{
      background: "rgba(0,0,0,0.5)", borderRadius: 8,
      border: "1px solid rgba(245, 158, 11, 0.18)",
      padding: 12,
      maxHeight: 360, overflowY: "auto",
    }}>
      <div style={{ fontSize: 11, color: "#fbbf24",
                     letterSpacing: "0.2em", marginBottom: 10,
                     borderBottom: "1px dashed rgba(245, 158, 11, 0.18)",
                     paddingBottom: 6 }}>
        📜 EVENT FEED · {events.length} recent
      </div>

      {events.map((e, i) => {
        const style = EVENT_STYLE[e.event_type] || { color: "#fff", icon: "•", label: e.event_type };
        const isFuture = cursorActive && e.t > cursorTs;
        const isHighlight = momentIds.has(e.event_id);
        const intensity = e.severity ?? 0.5;

        return (
          <div key={e.event_id || i}
               style={{
                 display: "flex", gap: 10,
                 padding: "8px 6px",
                 borderBottom: "1px solid rgba(255,255,255,0.04)",
                 opacity: isFuture ? 0.28 : 1,
                 transition: "opacity 0.2s ease",
                 background: isHighlight
                   ? "linear-gradient(90deg, rgba(251, 191, 36, 0.08) 0%, transparent 100%)"
                   : "transparent",
                 borderLeft: isHighlight
                   ? "2px solid #fbbf24"
                   : `2px solid ${style.color}33`,
               }}>
            <div style={{ fontSize: 14 }}>{style.icon}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 10, letterSpacing: "0.12em",
                color: style.color, fontWeight: 600,
                marginBottom: 2,
              }}>
                {style.label}
                {isHighlight && (
                  <span style={{ marginLeft: 8, color: "#fbbf24" }}>★ BOSS MOMENT</span>
                )}
              </div>
              <div style={{ fontSize: 12, color: "#e8e6dc",
                             lineHeight: 1.4 }}>
                {e.description || "(no description)"}
              </div>
              <div style={{ fontSize: 9, color: "#5e5a52",
                             marginTop: 2, letterSpacing: "0.06em" }}>
                {e.iso ? e.iso.slice(11, 19) + " UTC" : ""}
                {e.actors?.length > 0 && (
                  <span style={{ marginLeft: 8 }}>actors: {e.actors.join(", ")}</span>
                )}
              </div>
            </div>
            <div style={{
              width: 3, alignSelf: "stretch",
              background: `linear-gradient(180deg, ${style.color} 0%, transparent 100%)`,
              opacity: intensity,
              borderRadius: 2,
            }} />
          </div>
        );
      })}
    </div>
  );
}
