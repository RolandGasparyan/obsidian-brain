/**
 * ReplayMiniMap.jsx — heatmap of event density across timeline
 *
 * 🛡 READ-ONLY UI · renders /api/battle/replay-heatmap.json
 *
 * Each bar = one time-bucket. Height = event count. Color = dominant event type.
 * Click on bar = scrub to that bucket's start time.
 */

import React from "react";

const TYPE_COLOR = {
  AGENT_LEADER_CHANGE: "#fbbf24",
  XP_JUMP:             "#22c55e",
  XP_COLLAPSE:         "#ef4444",
  REGIME_TRANSITION:   "#06b6d4",
  VOLATILITY_STORM:    "#a855f7",
  CROWD_REACTION:      "#ec4899",
  BOSS_EVENT:          "#facc15",
  STREAK:              "#f59e0b",
  CHAMPION_SWAP:       "#fbbf24",
};

export default function ReplayMiniMap({
  heatmap,        // { buckets: [{ bucket, count, max_severity, dominant_type, ... }] }
  timeline,       // { timeline: { first_ts, last_ts, duration_seconds, count } }
  cursorTs,
  onSeek,
}) {
  if (!heatmap?.buckets?.length || !timeline?.timeline) {
    return (
      <div style={{
        height: 56, borderRadius: 8,
        background: "rgba(0, 0, 0, 0.35)",
        border: "1px dashed rgba(245, 158, 11, 0.15)",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#5e5a52", letterSpacing: "0.18em", fontSize: 10,
      }}>📡 awaiting heatmap…</div>
    );
  }

  const { first_ts, duration_seconds } = timeline.timeline;
  const span = duration_seconds || 1;
  const nBuckets = heatmap.buckets.length;
  const maxCount = Math.max(1, ...heatmap.buckets.map(b => b.count || 0));
  const cursorPct = cursorTs !== null
    ? Math.max(0, Math.min(100, ((cursorTs - first_ts) / span) * 100))
    : null;

  return (
    <div style={{
      position: "relative",
      display: "flex",
      gap: 1,
      height: 56,
      background: "rgba(0, 0, 0, 0.5)",
      border: "1px solid rgba(245, 158, 11, 0.18)",
      borderRadius: 8,
      padding: "4px 6px",
      overflow: "hidden",
    }}>
      {heatmap.buckets.map((b, i) => {
        const heightPct = (b.count / maxCount) * 100;
        const color = TYPE_COLOR[b.dominant_type] || "#5e5a52";
        const bucketTs = first_ts + (i / nBuckets) * span;
        return (
          <div key={i}
               onClick={() => onSeek?.(bucketTs)}
               title={b.count > 0
                 ? `bucket ${i}: ${b.count} events · ${b.dominant_type} dominant · max sev ${b.max_severity}`
                 : `bucket ${i}: silent`}
               style={{
                 flex: 1,
                 alignSelf: "flex-end",
                 height: `${Math.max(2, heightPct)}%`,
                 background: b.count > 0
                   ? `linear-gradient(180deg, ${color} 0%, ${color}80 100%)`
                   : "rgba(255, 255, 255, 0.04)",
                 boxShadow: b.count > 0
                   ? `0 0 6px ${color}66`
                   : "none",
                 cursor: "pointer",
                 borderRadius: 1,
                 minWidth: 2,
                 transition: "all 0.15s ease",
               }} />
        );
      })}

      {/* Cursor overlay */}
      {cursorPct !== null && (
        <div style={{
          position: "absolute",
          left: `${cursorPct}%`,
          top: 0, bottom: 0, width: 1,
          background: "rgba(251, 191, 36, 0.7)",
          boxShadow: "0 0 6px rgba(251, 191, 36, 0.5)",
          pointerEvents: "none",
        }} />
      )}

      <div style={{
        position: "absolute", left: 8, top: 4,
        fontSize: 9, color: "#5e5a52", letterSpacing: "0.16em",
        pointerEvents: "none",
      }}>HEATMAP</div>
    </div>
  );
}
