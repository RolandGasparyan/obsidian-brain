/**
 * ReplayTimeline.jsx — draggable/scrubbable timeline with glowing markers
 *
 * 🛡 READ-ONLY UI · operates on already-fetched JSON.
 */

import React, { useRef, useState, useEffect } from "react";

export default function ReplayTimeline({
  timeline,         // { timeline: {first_ts, last_ts, duration_seconds, count}, markers: [...] }
  cursorTs,         // current unix ts (or null)
  isLive,           // true = pinned to right edge
  onScrub,          // (ts) => void
  bossMoments = [], // array of { t, type, severity, description }
}) {
  const trackRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  if (!timeline?.timeline || !timeline.markers?.length) {
    return (
      <div style={{
        height: 64, borderRadius: 8,
        background: "rgba(245, 158, 11, 0.04)",
        border: "1px dashed rgba(245, 158, 11, 0.18)",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#5e5a52", letterSpacing: "0.16em", fontSize: 11,
      }}>⏳ awaiting replay timeline data…</div>
    );
  }

  const { first_ts, last_ts, duration_seconds } = timeline.timeline;
  const span = duration_seconds || 1;
  const effective_cursor = isLive ? last_ts : (cursorTs ?? last_ts);
  const cursorPct = Math.max(0, Math.min(100, ((effective_cursor - first_ts) / span) * 100));

  function tsFromX(clientX) {
    const rect = trackRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
    const pct = x / rect.width;
    return first_ts + pct * span;
  }

  function handleDown(e) {
    setDragging(true);
    onScrub(tsFromX(e.clientX));
  }
  function handleMove(e) {
    if (!dragging) return;
    onScrub(tsFromX(e.clientX));
  }
  function handleUp() { setDragging(false); }

  useEffect(() => {
    if (!dragging) return;
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, [dragging]);

  return (
    <div ref={trackRef}
         onMouseDown={handleDown}
         style={{
           position: "relative", height: 72,
           background: "rgba(0, 0, 0, 0.5)",
           border: "1px solid rgba(245, 158, 11, 0.25)",
           borderRadius: 10,
           cursor: dragging ? "grabbing" : "pointer",
           overflow: "hidden",
           userSelect: "none",
         }}>

      {/* Sparse tick markers */}
      {timeline.markers.map((m, i) => {
        const pct = ((m.t - first_ts) / span) * 100;
        return (
          <div key={i} style={{
            position: "absolute", left: `${pct}%`,
            top: 0, bottom: 0,
            width: 1,
            background: i % 12 === 0
              ? "rgba(245, 158, 11, 0.45)"
              : "rgba(255, 255, 255, 0.06)",
          }} />
        );
      })}

      {/* Boss moments → glowing pulses */}
      {bossMoments.map((m, i) => {
        const pct = ((m.t - first_ts) / span) * 100;
        if (pct < 0 || pct > 100) return null;
        return (
          <div key={`boss-${i}`}
               title={`${m.type}: ${m.description}`}
               style={{
                 position: "absolute", left: `${pct}%`,
                 top: 6, transform: "translateX(-50%)",
                 width: 12, height: 12,
                 borderRadius: "50%",
                 background: "radial-gradient(circle, #fbbf24 0%, rgba(245, 158, 11, 0.0) 70%)",
                 boxShadow: "0 0 12px rgba(251, 191, 36, 0.7)",
                 animation: "tg-boss-pulse 2.5s ease-in-out infinite",
                 pointerEvents: "none",
               }} />
        );
      })}

      {/* Scrubber cursor */}
      <div style={{
        position: "absolute", left: `${cursorPct}%`,
        top: 0, bottom: 0, width: 2,
        background: "linear-gradient(180deg, transparent 0%, #fbbf24 50%, transparent 100%)",
        boxShadow: "0 0 16px rgba(251, 191, 36, 0.85)",
        transform: "translateX(-50%)",
        pointerEvents: "none",
      }}>
        <div style={{
          position: "absolute", top: -4, left: "50%",
          transform: "translateX(-50%)",
          width: 10, height: 10, borderRadius: "50%",
          background: "#fbbf24",
          boxShadow: "0 0 12px rgba(251, 191, 36, 1)",
        }} />
        <div style={{
          position: "absolute", bottom: -22, left: "50%",
          transform: "translateX(-50%)",
          fontSize: 10, color: "#fbbf24",
          whiteSpace: "nowrap", letterSpacing: "0.1em",
        }}>
          {new Date(effective_cursor * 1000).toISOString().slice(11, 19)} UTC
        </div>
      </div>

      {/* LIVE badge */}
      {isLive && (
        <div style={{
          position: "absolute", top: 8, right: 12,
          fontSize: 10, color: "#22c55e",
          letterSpacing: "0.2em",
        }}>● LIVE</div>
      )}

      <style>{`
        @keyframes tg-boss-pulse {
          0%, 100% { opacity: 0.8; transform: translateX(-50%) scale(1); }
          50%      { opacity: 1.0; transform: translateX(-50%) scale(1.4); }
        }
      `}</style>
    </div>
  );
}
