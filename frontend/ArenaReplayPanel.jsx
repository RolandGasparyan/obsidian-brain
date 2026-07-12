/**
 * ArenaReplayPanel.jsx — main container for the replay experience
 *
 * 🛡 PAPER-SAFE · READ-ONLY · displays history from /api/battle/replay-*.json
 *
 * Polls 5 endpoints and composes the full replay UI:
 *   - replay-index.json       general status + storage health
 *   - replay-timeline.json    sparse scrubber markers
 *   - replay-events-recent.json  rolling event feed
 *   - replay-bosses.json      auto-tagged boss moments
 *   - replay-heatmap.json     event-density minimap
 *
 * Modes (operator-requested):
 *   • cinematic      — bold motion · large transitions
 *   • tactical       — dense data · multiple panels visible
 *   • minimal        — clean · scrubber + crowd only
 *   • auto-highlight — auto-cycles through boss moments
 *
 * Style: black/gold esports · glowing timeline · cinematic transitions
 */

import React, { useEffect, useRef, useState } from "react";
import ReplayTimeline from "./ReplayTimeline.jsx";
import ReplayControls from "./ReplayControls.jsx";
import ReplayEventFeed from "./ReplayEventFeed.jsx";
import ReplayMiniMap from "./ReplayMiniMap.jsx";

const ENDPOINTS = {
  index:    "/api/battle/replay-index.json",
  timeline: "/api/battle/replay-timeline.json",
  events:   "/api/battle/replay-events-recent.json",
  bosses:   "/api/battle/replay-bosses.json",
  heatmap:  "/api/battle/replay-heatmap.json",
};

const POLL_MS = 10_000;

export default function ArenaReplayPanel() {
  const [data, setData] = useState({
    index: null, timeline: null, events: null, bosses: null, heatmap: null,
  });
  const [cursorTs, setCursorTs] = useState(null);     // active scrubber position
  const [isLive, setIsLive] = useState(true);          // true = follow current
  const [mode, setMode] = useState("cinematic");       // cinematic | tactical | minimal | auto-highlight
  const [playRate, setPlayRate] = useState(1);         // 1x | 2x | 4x | 8x
  const autoHighlightRef = useRef({ idx: 0, lastSwitchTs: 0 });

  // Polling loop
  useEffect(() => {
    let cancelled = false;
    async function fetchAll() {
      try {
        const [index, timeline, events, bosses, heatmap] = await Promise.all([
          fetch(ENDPOINTS.index).then(r => r.ok ? r.json() : null),
          fetch(ENDPOINTS.timeline).then(r => r.ok ? r.json() : null),
          fetch(ENDPOINTS.events).then(r => r.ok ? r.json() : null),
          fetch(ENDPOINTS.bosses).then(r => r.ok ? r.json() : null),
          fetch(ENDPOINTS.heatmap).then(r => r.ok ? r.json() : null),
        ]);
        if (!cancelled) {
          setData({ index, timeline, events, bosses, heatmap });
          if (isLive && timeline?.timeline?.last_ts) {
            setCursorTs(timeline.timeline.last_ts);
          }
        }
      } catch (e) {
        console.warn("[ArenaReplay] poll failed:", e);
      }
    }
    fetchAll();
    const id = setInterval(fetchAll, POLL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, [isLive]);

  // Auto-highlight mode: cycle through boss moments every 15s
  useEffect(() => {
    if (mode !== "auto-highlight" || !data.bosses?.moments?.length) return;
    const id = setInterval(() => {
      const moments = data.bosses.moments;
      const ref = autoHighlightRef.current;
      ref.idx = (ref.idx + 1) % moments.length;
      const target = moments[ref.idx];
      if (target?.t) {
        setIsLive(false);
        setCursorTs(target.t);
      }
    }, 15_000);
    return () => clearInterval(id);
  }, [mode, data.bosses]);

  const sceneStyle = {
    cinematic: { background: "linear-gradient(135deg, #0a0608 0%, #1a0f00 50%, #000 100%)",
                  padding: 28, gap: 24 },
    tactical:  { background: "#0a0a0e", padding: 16, gap: 12 },
    minimal:   { background: "#000", padding: 12, gap: 8 },
    "auto-highlight": { background: "radial-gradient(ellipse at center, #1a0f00 0%, #000 100%)",
                         padding: 24, gap: 20 },
  }[mode];

  return (
    <div className="arena-replay-panel" style={{
      color: "#fff8e7",
      fontFamily: "'JetBrains Mono', monospace",
      borderRadius: 14,
      border: "1px solid rgba(245, 158, 11, 0.35)",
      boxShadow: "0 0 32px rgba(245, 158, 11, 0.18), inset 0 0 18px rgba(0,0,0,0.6)",
      display: "flex",
      flexDirection: "column",
      ...sceneStyle,
    }}>
      <header style={{ display: "flex", justifyContent: "space-between",
                        alignItems: "center", marginBottom: 8 }}>
        <h2 style={{
          fontSize: 22, margin: 0, letterSpacing: "0.18em",
          background: "linear-gradient(90deg, #fbbf24, #f59e0b, #ea7c30)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          fontWeight: 700,
        }}>⚔️ ARENA REPLAY</h2>
        <span style={{
          fontSize: 11, color: "#8a8478", letterSpacing: "0.18em",
        }}>
          {data.index ? `${data.index.snapshot_count_recent ?? 0} cycles · ${data.index.event_count_recent ?? 0} events` : "loading..."}
          {data.index?.tg_safe && (
            <span style={{ marginLeft: 12, color: "#22c55e" }}>● TG_SAFE</span>
          )}
        </span>
      </header>

      <ReplayMiniMap
        heatmap={data.heatmap}
        timeline={data.timeline}
        cursorTs={cursorTs}
        onSeek={(ts) => { setIsLive(false); setCursorTs(ts); }}
      />

      <ReplayTimeline
        timeline={data.timeline}
        cursorTs={cursorTs}
        isLive={isLive}
        onScrub={(ts) => { setIsLive(false); setCursorTs(ts); }}
        bossMoments={data.bosses?.moments || []}
      />

      <ReplayControls
        isLive={isLive}
        playRate={playRate}
        mode={mode}
        onLiveToggle={() => setIsLive(v => !v)}
        onRateChange={setPlayRate}
        onModeChange={setMode}
        onJumpRewind={(seconds) => {
          if (!data.timeline?.timeline?.last_ts) return;
          setIsLive(false);
          setCursorTs((cursorTs || data.timeline.timeline.last_ts) - seconds);
        }}
      />

      {mode !== "minimal" && (
        <div style={{ display: "grid",
                      gridTemplateColumns: mode === "tactical" ? "1fr 1fr" : "1fr",
                      gap: 16 }}>
          <ReplayEventFeed
            events={data.events?.events || []}
            cursorTs={cursorTs}
            highlightMoments={data.bosses?.moments || []}
          />
          {mode === "tactical" && data.bosses?.moments?.length > 0 && (
            <BossMomentsList moments={data.bosses.moments}
              onSelect={(m) => { setIsLive(false); setCursorTs(m.t); }} />
          )}
        </div>
      )}

      <footer style={{
        fontSize: 10, color: "#5e5a52", letterSpacing: "0.14em",
        marginTop: 4, paddingTop: 8,
        borderTop: "1px dashed rgba(245, 158, 11, 0.15)",
      }}>
        🛡 PAPER ONLY · READ ONLY · NO LIVE ORDERS · cursor={cursorTs ? new Date(cursorTs * 1000).toISOString() : "—"}
      </footer>
    </div>
  );
}

// Auxiliary inline component for tactical mode
function BossMomentsList({ moments, onSelect }) {
  return (
    <div style={{
      background: "rgba(0,0,0,0.5)", borderRadius: 8,
      border: "1px solid rgba(245, 158, 11, 0.2)",
      padding: 12,
    }}>
      <div style={{ fontSize: 11, color: "#fbbf24", letterSpacing: "0.2em",
                     marginBottom: 8 }}>🏆 BOSS MOMENTS</div>
      {moments.map((m, i) => (
        <div key={m.event_id || i} onClick={() => onSelect(m)}
             style={{
               cursor: "pointer", padding: "6px 4px",
               borderBottom: "1px solid rgba(255,255,255,0.04)",
               fontSize: 12,
             }}>
          <span style={{ color: "#f59e0b" }}>{m.type}</span> · {m.description}
        </div>
      ))}
    </div>
  );
}
