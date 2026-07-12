/* tradingguru.ai — corrected design · live data wiring
 *
 * Reads from two sources, in this order:
 *
 *   1. Gate.io public spot tickers
 *        https://api.gateio.ws/api/v4/spot/tickers
 *      — read-only · no auth · used to render BTC/ETH/XRP/SOL last/change/24h.
 *
 *   2. Battle telemetry published by canary_executor.publish_status()
 *        /api/battle/terminal.json    (frontend-shaped real state)
 *        /api/battle/live_battle.json (raw fallback if terminal not present)
 *        /api/battle/replay-*.json    (5 endpoints for the arena page)
 *      — real per-account state from the 3 Gate.io spot accounts under L1
 *        governance · paper/live state as published, no fabrications.
 *
 * Rules:
 *   • Never invent numbers. If a value is missing, render `—`.
 *   • Never inject placeholder rows / agent names. Empty stays empty.
 *   • Polls every 10s. Stops polling when the tab is hidden.
 */

(function () {
  "use strict";

  const POLL_MS = 10_000;
  const DASH = "—";

  const PAIRS = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT"];
  const GATE_PAIRS = PAIRS.map((p) => p.replace("/", "_"));

  const ENDPOINTS = {
    terminal: "/api/battle/terminal.json",
    live: "/api/battle/live_battle.json",
    replayIndex: "/api/battle/replay-index.json",
    replayTimeline: "/api/battle/replay-timeline.json",
    replayEvents: "/api/battle/replay-events-recent.json",
    replayBosses: "/api/battle/replay-bosses.json",
    replayHeatmap: "/api/battle/replay-heatmap.json",
    gateTickers: "https://api.gateio.ws/api/v4/spot/tickers",
  };

  // ── DOM helpers ────────────────────────────────────────────────────────
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function setAll(sel, text, klass) {
    $$(sel).forEach((el) => {
      el.textContent = text == null || text === "" ? DASH : text;
      if (klass) {
        el.classList.remove("green", "red", "amber", "cyan");
        if (klass !== "neutral") el.classList.add(klass);
      }
    });
  }

  // ── Format helpers ─────────────────────────────────────────────────────
  function fmtUSD(n, decimals = 2) {
    if (n == null || isNaN(n)) return DASH;
    return (
      "$" +
      Number(n).toLocaleString("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })
    );
  }

  function fmtSignedUSD(n) {
    if (n == null || isNaN(n)) return DASH;
    const sign = n > 0 ? "+" : n < 0 ? "-" : "";
    return sign + fmtUSD(Math.abs(n));
  }

  function fmtPct(n) {
    if (n == null || isNaN(n)) return DASH;
    const sign = n > 0 ? "+" : "";
    return sign + Number(n).toFixed(2) + "%";
  }

  function fmtPrice(n) {
    if (n == null || isNaN(n)) return DASH;
    if (n >= 1000) return Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 });
    if (n >= 1) return Number(n).toFixed(4);
    return Number(n).toFixed(6);
  }

  function fmtInt(n) {
    if (n == null || isNaN(n)) return DASH;
    return Number(n).toLocaleString("en-US");
  }

  function fmtTime(iso) {
    if (!iso) return DASH;
    const d = new Date(iso);
    if (isNaN(d.getTime())) return DASH;
    return d.toISOString().replace("T", " ").replace(/\.\d+Z$/, " UTC");
  }

  function pnlClass(v) {
    if (v == null || isNaN(v) || v === 0) return "neutral";
    return v > 0 ? "green" : "red";
  }

  // ── Fetch helpers ──────────────────────────────────────────────────────
  async function fetchJSON(url, signal) {
    try {
      const res = await fetch(url, { cache: "no-store", signal });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
  }

  async function loadTickers(signal) {
    const data = await fetchJSON(ENDPOINTS.gateTickers, signal);
    if (!Array.isArray(data)) return null;
    const out = {};
    for (const t of data) {
      if (!t || !t.currency_pair) continue;
      if (!GATE_PAIRS.includes(t.currency_pair)) continue;
      out[t.currency_pair] = {
        last: parseFloat(t.last),
        change_pct: parseFloat(t.change_percentage),
        high_24h: parseFloat(t.high_24h),
        low_24h: parseFloat(t.low_24h),
        volume_24h: parseFloat(t.base_volume),
      };
    }
    return Object.keys(out).length ? out : null;
  }

  async function loadBattle(signal) {
    const t = await fetchJSON(ENDPOINTS.terminal, signal);
    if (t) return { source: "terminal", data: t };
    const l = await fetchJSON(ENDPOINTS.live, signal);
    if (l) return { source: "live", data: l };
    return null;
  }

  async function loadReplay(signal) {
    const [idx, tl, ev, bs, hm] = await Promise.all([
      fetchJSON(ENDPOINTS.replayIndex, signal),
      fetchJSON(ENDPOINTS.replayTimeline, signal),
      fetchJSON(ENDPOINTS.replayEvents, signal),
      fetchJSON(ENDPOINTS.replayBosses, signal),
      fetchJSON(ENDPOINTS.replayHeatmap, signal),
    ]);
    return { index: idx, timeline: tl, events: ev, bosses: bs, heatmap: hm };
  }

  // ── Renderers ──────────────────────────────────────────────────────────
  function renderConnStatus(battle, tickers) {
    const parts = [];
    if (battle) parts.push("L1 telemetry · " + fmtTime(battle.data && battle.data.timestamp));
    else parts.push("L1 telemetry · offline");
    if (tickers) parts.push("Gate.io tickers · live");
    else parts.push("Gate.io tickers · offline");
    setAll("[data-conn-status]", parts.join(" · "));
  }

  function renderTickers(tickers) {
    $$("[data-ticker]").forEach((el) => {
      const key = el.dataset.ticker;
      const field = el.dataset.field || "last";
      const t = tickers && tickers[key];
      if (!t) {
        el.textContent = DASH;
        el.classList.remove("green", "red");
        return;
      }
      if (field === "last") el.textContent = fmtPrice(t.last);
      else if (field === "change_pct") {
        el.textContent = fmtPct(t.change_pct);
        el.classList.toggle("green", t.change_pct > 0);
        el.classList.toggle("red", t.change_pct < 0);
      } else if (field === "high_24h") el.textContent = fmtPrice(t.high_24h);
      else if (field === "low_24h") el.textContent = fmtPrice(t.low_24h);
      else if (field === "volume_24h") el.textContent = fmtInt(Math.round(t.volume_24h));
    });
  }

  function renderBattle(battle) {
    if (!battle || !battle.data) {
      // wipe to dashes — never leave stale numbers on screen
      $$("[data-battle]").forEach((el) => {
        el.textContent = DASH;
        el.classList.remove("green", "red");
      });
      $$("[data-slot]").forEach((el) => {
        if (el.dataset.field !== "strategy") {
          el.textContent = DASH;
          el.classList.remove("green", "red");
        }
      });
      $$("[data-lb-row]").forEach((row) => {
        $$("[data-field]", row).forEach((el) => (el.textContent = DASH));
      });
      return;
    }

    const d = battle.data;

    // Aggregate fields (index.html status strip + agents page header)
    setAll('[data-battle="capital"]', fmtUSD(d.real_capital_usd, 2));
    setAll('[data-battle="alive_accounts"]',
      d.live && d.live.alive_accounts != null && d.live.total_accounts != null
        ? d.live.alive_accounts + " / " + d.live.total_accounts
        : DASH);
    setAll('[data-battle="aggregate_pnl"]',
      d.live ? fmtSignedUSD(d.live.aggregate_session_pnl_usd) : DASH);
    setAll('[data-battle="aggregate_trades"]',
      d.live ? fmtInt(d.live.aggregate_trades_today) : DASH);
    setAll('[data-battle="strategy"]', d.strategy || DASH);
    setAll('[data-battle="mode"]', d.mode || DASH);
    setAll('[data-battle="timestamp"]', fmtTime(d.timestamp));

    // pnl colour
    if (d.live) {
      $$('[data-battle="aggregate_pnl"]').forEach((el) => {
        el.classList.remove("green", "red");
        const cls = pnlClass(d.live.aggregate_session_pnl_usd);
        if (cls !== "neutral") el.classList.add(cls);
      });
    }

    // Per-account slot cards (agents.html) — keyed by data-slot index 1..N
    // and resolved deterministically against the order in d.accounts.
    const accountIds = d.accounts ? Object.keys(d.accounts) : [];
    $$("[data-slot]").forEach((el) => {
      const slot = parseInt(el.dataset.slot, 10);
      const field = el.dataset.field;
      if (!slot || !field) return;
      if (field === "strategy") return; // strategy column is hardcoded MA50W10
      const id = accountIds[slot - 1];
      const acc = id && d.accounts ? d.accounts[id] : null;
      if (!acc) {
        el.textContent = DASH;
        el.classList.remove("green", "red");
        return;
      }
      switch (field) {
        case "account_id":
          el.textContent = id;
          break;
        case "status":
          el.textContent = acc.status || DASH;
          el.classList.toggle("green", acc.status === "LIVE");
          el.classList.toggle("red", acc.status === "DEAD");
          break;
        case "capital":
          el.textContent = fmtUSD(acc.capital_usd);
          break;
        case "pnl":
          el.textContent = fmtSignedUSD(acc.session_pnl_usd);
          el.classList.remove("green", "red");
          {
            const cls = pnlClass(acc.session_pnl_usd);
            if (cls !== "neutral") el.classList.add(cls);
          }
          break;
        case "trades":
          el.textContent = fmtInt(acc.trades_today);
          break;
        case "open_positions":
          el.textContent = fmtInt(acc.open_positions);
          break;
        case "daily_dd":
          el.textContent = fmtUSD(acc.daily_dd_usd);
          break;
        default:
          el.textContent = DASH;
      }
    });

    // Championship 60-min rounds banner (leaderboard.html)
    renderChampionship(d);

    // Leaderboard rows (leaderboard.html) — rank by round_pnl_usd of the
    // current (in-progress) round, falling back to session_pnl_usd if the
    // championship block is missing (e.g. terminal.json predates round support).
    const rows = $$("[data-lb-row]");
    if (rows.length && d.accounts) {
      const champ = d.championship || null;
      const currentRound = champ && champ.rounds
        ? champ.rounds.find((r) => r.in_progress)
        : null;
      const roundPnlById = {};
      if (currentRound && Array.isArray(currentRound.champions)) {
        currentRound.champions.forEach((c) => {
          if (c && c.account_id != null) {
            roundPnlById[c.account_id] = (c.round_pnl_usd != null)
              ? Number(c.round_pnl_usd)
              : null;
          }
        });
      }
      const ranked = Object.entries(d.accounts)
        .map(([id, a]) => ({
          id,
          status: a.status,
          round_pnl: roundPnlById[id] != null ? roundPnlById[id] : null,
          pnl: Number(a.session_pnl_usd || 0),
          trades: Number(a.trades_today || 0),
          capital: Number(a.capital_usd || 0),
        }))
        .sort((a, b) => {
          // Rank primarily by round_pnl (if any round data), else by session PnL.
          const ar = a.round_pnl != null ? a.round_pnl : -Infinity;
          const br = b.round_pnl != null ? b.round_pnl : -Infinity;
          if (ar !== br) return br - ar;
          return b.pnl - a.pnl;
        });
      rows.forEach((row, i) => {
        const r = ranked[i];
        const fields = {
          agent: r ? r.id : DASH,
          round_pnl: r && r.round_pnl != null ? fmtSignedUSD(r.round_pnl) : DASH,
          pnl: r ? fmtSignedUSD(r.pnl) : DASH,
          trades: r ? fmtInt(r.trades) : DASH,
          capital: r ? fmtUSD(r.capital) : DASH,
          status: r ? r.status : DASH,
        };
        $$("[data-field]", row).forEach((el) => {
          const key = el.dataset.field;
          el.textContent = fields[key] != null ? fields[key] : DASH;
          if ((key === "pnl" || key === "round_pnl") && r) {
            el.classList.remove("green", "red");
            const val = key === "pnl" ? r.pnl : r.round_pnl;
            const cls = pnlClass(val);
            if (cls !== "neutral") el.classList.add(cls);
          }
          if (key === "status" && r) {
            el.classList.toggle("green", r.status === "LIVE");
            el.classList.toggle("red", r.status === "DEAD");
          }
        });
      });
    }
  }

  // ── 60-min championship rounds ─────────────────────────────────────────
  function renderChampionship(d) {
    const champ = d && d.championship;
    const banner = document.querySelector('[data-championship="banner"]');
    if (!banner) return; // page doesn't have a championship banner

    if (!champ) {
      setAll('[data-championship="current_round_id"]', DASH);
      setAll('[data-championship="current_round_leader"]', DASH);
      setAll('[data-championship="overall_leader"]', DASH);
      setAll('[data-championship="round_elapsed"]', DASH);
      setAll('[data-championship="round_interval"]', DASH);
      const bar = document.querySelector('[data-championship="round_progress_bar"]');
      if (bar) bar.style.width = "0%";
      const body = document.querySelector('[data-championship="completed_rounds_body"]');
      if (body) body.innerHTML =
        '<tr><td colspan="7" class="empty-cell">— telemetry feed offline —</td></tr>';
      return;
    }

    const intervalSec = Number(champ.round_interval_sec || 0);
    const minutes = Math.round(intervalSec / 60);
    setAll('[data-championship="round_interval"]',
      minutes > 0 ? minutes + "m" : DASH);

    setAll('[data-championship="current_round_id"]',
      champ.current_round_id != null ? "#" + champ.current_round_id : DASH);
    setAll('[data-championship="current_round_leader"]',
      champ.current_round_leader || DASH);
    setAll('[data-championship="overall_leader"]',
      champ.overall_leader || DASH);

    // Elapsed within the current round
    const current = (champ.rounds || []).find((r) => r.in_progress);
    if (current && current.started_at && intervalSec > 0) {
      const startedMs = Date.parse(current.started_at);
      if (!isNaN(startedMs)) {
        const elapsedSec = Math.max(0, Math.min(intervalSec,
          (Date.now() - startedMs) / 1000));
        const m = Math.floor(elapsedSec / 60);
        const s = Math.floor(elapsedSec % 60);
        setAll('[data-championship="round_elapsed"]',
          m + "m " + (s < 10 ? "0" + s : s) + "s");
        const bar = document.querySelector('[data-championship="round_progress_bar"]');
        if (bar) bar.style.width = ((elapsedSec / intervalSec) * 100).toFixed(1) + "%";
      }
    } else {
      setAll('[data-championship="round_elapsed"]', DASH);
      const bar = document.querySelector('[data-championship="round_progress_bar"]');
      if (bar) bar.style.width = "0%";
    }

    // Completed rounds history
    const body = document.querySelector('[data-championship="completed_rounds_body"]');
    if (body) {
      const completed = (champ.rounds || []).filter((r) => !r.in_progress);
      if (!completed.length) {
        body.innerHTML =
          '<tr><td colspan="7" class="empty-cell">— no completed rounds yet — first crown lands when round 1 closes —</td></tr>';
      } else {
        const accIds = d.accounts ? Object.keys(d.accounts) : ["MAIN", "SUB1", "SUB2"];
        body.innerHTML = completed.slice(0, 12).map((r) => {
          const champById = {};
          (r.champions || []).forEach((c) => {
            if (c && c.account_id != null) champById[c.account_id] = c;
          });
          const winnerPnl = r.winner_account_id && champById[r.winner_account_id]
            ? champById[r.winner_account_id].round_pnl_usd
            : null;
          const accCells = accIds.map((aid) => {
            const c = champById[aid];
            if (!c || c.round_pnl_usd == null) {
              return '<td class="dash">' + DASH + "</td>";
            }
            const v = Number(c.round_pnl_usd);
            const cls = pnlClass(v);
            const klass = cls === "neutral" ? "" : (' class="' + cls + '"');
            const tag = r.winner_account_id === aid ? " 🏆" : "";
            return "<td" + klass + ">" + fmtSignedUSD(v) + tag + "</td>";
          }).join("");
          return "<tr>" +
            '<td class="dash">#' + r.round_id + "</td>" +
            "<td>" + fmtTime(r.started_at) + "</td>" +
            "<td>" + (r.winner_account_id || DASH) + "</td>" +
            "<td>" + (winnerPnl != null ? fmtSignedUSD(winnerPnl) : DASH) + "</td>" +
            accCells +
          "</tr>";
        }).join("");
      }
    }
  }

  function renderReplay(rp) {
    // arena timeline cursor label
    const last = rp && rp.timeline && rp.timeline.timeline && rp.timeline.timeline.last_ts;
    setAll("[data-replay='cursor_label']",
      last ? "CURSOR · " + fmtTime(last) : "CURSOR · " + DASH);

    // event feed
    const feed = document.querySelector("[data-replay='event_feed']");
    if (feed) {
      const events = (rp && rp.events && rp.events.events) || [];
      if (!events.length) {
        feed.innerHTML =
          '<div class="empty-state"><span class="dash">' +
          DASH + " " + DASH + " " + DASH +
          "</span>No live cycle yet.<br/>The feed populates when a shadow round is active.</div>";
      } else {
        const max = 12;
        feed.innerHTML =
          '<ul class="event-feed-list">' +
          events.slice(-max).reverse().map((e) => {
            const t = fmtTime(e.ts || e.timestamp);
            const kind = (e.type || e.kind || "event").toString().toUpperCase();
            const txt = (e.text || e.msg || e.summary || "").toString();
            return '<li><span class="ts">' + t + "</span> <span class=\"kind\">" +
              kind + "</span> " + txt + "</li>";
          }).join("") +
          "</ul>";
      }
    }

    // boss moments
    const boss = document.querySelector("[data-replay='boss_moments']");
    if (boss) {
      const moments = (rp && rp.bosses && rp.bosses.moments) || [];
      if (!moments.length) {
        boss.innerHTML =
          '<div class="empty-state"><span class="dash">' +
          DASH + " " + DASH + " " + DASH +
          "</span>Auto-tagged moments appear here<br/>once telemetry is publishing.</div>";
      } else {
        boss.innerHTML =
          '<ul class="event-feed-list">' +
          moments.slice(-8).reverse().map((m) => {
            const t = fmtTime(m.ts || m.timestamp);
            const label = (m.label || m.kind || "BOSS").toString().toUpperCase();
            const note = (m.note || m.text || "").toString();
            return '<li><span class="ts">' + t + "</span> <span class=\"kind\">" +
              label + "</span> " + note + "</li>";
          }).join("") +
          "</ul>";
      }
    }

    // heatmap as 1-row sparkline
    const heat = document.querySelector("[data-replay='heatmap']");
    if (heat) {
      const buckets = (rp && rp.heatmap && rp.heatmap.buckets) || [];
      if (!buckets.length) {
        heat.innerHTML =
          '<div class="empty-state"><span class="dash">' +
          DASH + " " + DASH + " " + DASH +
          "</span>Event density renders here<br/>after the first cycle completes.</div>";
      } else {
        const max = Math.max(1, ...buckets.map((b) => b.count || 0));
        heat.innerHTML =
          '<div class="heat-row">' +
          buckets.map((b) => {
            const h = Math.round(((b.count || 0) / max) * 100);
            return '<span class="heat-cell" style="height:' + h + '%" title="' +
              (b.ts || "") + " · " + (b.count || 0) + ' events"></span>';
          }).join("") +
          "</div>";
      }
    }

    // cycle stats
    const stats = document.querySelector("[data-replay='cycle_stats']");
    if (stats) {
      const idx = rp && rp.index;
      if (!idx) {
        stats.innerHTML =
          '<div class="empty-state"><span class="dash">' +
          DASH + " " + DASH + " " + DASH +
          "</span>Cycles · events · drawdown<br/>shown only when measured, never estimated.</div>";
      } else {
        const rows = [
          ["CYCLES",        fmtInt(idx.cycle_count || idx.snapshots || idx.cycles)],
          ["EVENTS",        fmtInt(idx.event_count || idx.events)],
          ["LAST CYCLE",    fmtTime(idx.last_cycle_ts || idx.last_ts)],
          ["TG SAFE",       idx.tg_safe === true ? "YES" : idx.tg_safe === false ? "NO" : DASH],
        ];
        stats.innerHTML =
          '<table class="cycle-stat-tbl">' +
          rows.map((r) => "<tr><th>" + r[0] + "</th><td>" + (r[1] || DASH) + "</td></tr>").join("") +
          "</table>";
      }
    }
  }

  // ── Main tick ──────────────────────────────────────────────────────────
  let inflight = null;
  async function tick() {
    if (inflight) inflight.abort();
    inflight = new AbortController();
    const signal = inflight.signal;
    const wantsReplay = document.querySelector("[data-replay]") != null;
    try {
      const [tickers, battle, replay] = await Promise.all([
        loadTickers(signal),
        loadBattle(signal),
        wantsReplay ? loadReplay(signal) : Promise.resolve(null),
      ]);
      if (signal.aborted) return;
      renderConnStatus(battle, tickers);
      renderTickers(tickers);
      renderBattle(battle);
      if (wantsReplay) renderReplay(replay);
    } catch (e) {
      // swallow — UI already shows DASH from previous render or initial state
    }
  }

  let pollId = null;
  function start() {
    tick();
    if (pollId) clearInterval(pollId);
    pollId = setInterval(tick, POLL_MS);
  }
  function stop() {
    if (pollId) clearInterval(pollId);
    pollId = null;
  }

  document.addEventListener("DOMContentLoaded", () => {
    start();
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) stop();
      else start();
    });
  });

  // Exposed for tests / DevTools
  window.TG = Object.freeze({
    POLL_MS,
    ENDPOINTS,
    PAIRS,
    GATE_PAIRS,
    tick,
    start,
    stop,
    _fmt: { fmtUSD, fmtSignedUSD, fmtPct, fmtPrice, fmtInt, fmtTime, pnlClass },
  });
})();

/* ════════════════════════════════════════════════════════════════════════
   Retro Cyberpunk Galaxy World — cosmetic FX layer.
   Animated starfield + floating UFOs on a fixed canvas, vignette/flicker
   overlay, and synthesized arcade SFX (WebAudio — no asset files) behind a
   sound toggle, plus arcade button/nav juice. Self-contained: no network
   calls, no URL literals (the data layer above owns all fetching). Honors
   prefers-reduced-motion and pauses rendering when the tab is hidden.
   ════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  const RM = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const PALETTE = ["#c061ff", "#ff5fd2", "#4db5ff", "#4dffb0", "#ffd24d"];

  // ── Starfield + UFO canvas ─────────────────────────────────────────────
  function galaxy() {
    const c = document.createElement("canvas");
    c.id = "tg-galaxy";
    document.body.appendChild(c);
    const ctx = c.getContext("2d");
    if (!ctx) return;

    let w = 0, h = 0, dpr = 1;
    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = c.width = Math.floor(window.innerWidth * dpr);
      h = c.height = Math.floor(window.innerHeight * dpr);
      c.style.width = window.innerWidth + "px";
      c.style.height = window.innerHeight + "px";
    }
    resize();
    window.addEventListener("resize", resize);

    const LAYERS = [
      { col: "180,200,255", sz: 1, sp: 6 },
      { col: "200,150,255", sz: 2, sp: 14 },
      { col: "120,255,220", sz: 3, sp: 26 },
    ];
    const stars = [];
    for (let li = 0; li < LAYERS.length; li++) {
      const n = li === 0 ? 110 : li === 1 ? 60 : 28;
      for (let i = 0; i < n; i++) {
        stars.push({ x: Math.random() * w, y: Math.random() * h, l: li, tw: Math.random() * 6.28 });
      }
    }

    const ufos = [];
    function spawnUfo(seed) {
      ufos.push({
        x: seed ? Math.random() * w : -0.1 * w,
        y: (Math.random() * 0.55 + 0.05) * h,
        v: (Math.random() * 0.35 + 0.18) * dpr,
        s: (Math.random() * 10 + 13) * dpr,
        col: PALETTE[(Math.random() * PALETTE.length) | 0],
        bob: Math.random() * 6.28,
      });
    }
    for (let i = 0; i < 3; i++) spawnUfo(true);

    const shots = [];
    function maybeShot() {
      if (Math.random() < 0.012 && shots.length < 3) {
        shots.push({
          x: Math.random() * w, y: Math.random() * h * 0.5,
          vx: (Math.random() * 5 + 5) * dpr, vy: (Math.random() * 2 + 1) * dpr, life: 1,
        });
      }
    }

    function drawUfo(u) {
      const x = u.x, y = u.y + Math.sin(u.bob) * 4 * dpr, s = u.s;
      ctx.save();
      ctx.shadowColor = u.col; ctx.shadowBlur = 16 * dpr; ctx.fillStyle = u.col;
      ctx.fillRect(x - s * 0.3, y - s * 0.5, s * 0.6, s * 0.28);    // dome
      ctx.fillRect(x - s * 0.75, y - s * 0.22, s * 1.5, s * 0.3);   // saucer
      ctx.fillStyle = "rgba(255,255,255,0.92)";
      for (let i = -1; i <= 1; i++) {
        ctx.fillRect(x + i * s * 0.42 - s * 0.06, y + s * 0.14, s * 0.12, s * 0.12);
      }
      ctx.restore();
    }

    function step(moving) {
      ctx.clearRect(0, 0, w, h);
      for (const st of stars) {
        const L = LAYERS[st.l];
        if (moving) {
          st.x -= L.sp * 0.016;
          if (st.x < 0) { st.x = w; st.y = Math.random() * h; }
          st.tw += 0.03;
        }
        let a = 0.45 + Math.sin(st.tw) * 0.35;
        if (a < 0) a = 0;
        ctx.fillStyle = "rgba(" + L.col + "," + a.toFixed(3) + ")";
        ctx.fillRect(st.x | 0, st.y | 0, L.sz * dpr, L.sz * dpr);
      }
      if (moving) {
        maybeShot();
        for (let i = shots.length - 1; i >= 0; i--) {
          const s = shots[i];
          ctx.strokeStyle = "rgba(255,255,255," + s.life.toFixed(2) + ")";
          ctx.lineWidth = 2 * dpr;
          ctx.beginPath();
          ctx.moveTo(s.x, s.y);
          ctx.lineTo(s.x - s.vx * 4, s.y - s.vy * 4);
          ctx.stroke();
          s.x += s.vx; s.y += s.vy; s.life -= 0.02;
          if (s.life <= 0) shots.splice(i, 1);
        }
      }
      for (const u of ufos) {
        if (moving) {
          u.x += u.v; u.bob += 0.05;
          if (u.x > w + 0.1 * w) { u.x = -0.1 * w; u.y = (Math.random() * 0.55 + 0.05) * h; }
        }
        drawUfo(u);
      }
    }

    let raf = 0, running = false;
    function loop() { step(true); raf = requestAnimationFrame(loop); }
    function startFx() { if (RM || running) return; running = true; loop(); }
    function stopFx() { running = false; if (raf) cancelAnimationFrame(raf); raf = 0; }

    if (RM) {
      step(false);
    } else {
      startFx();
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) stopFx(); else startFx();
      });
    }
  }

  // ── Vignette / flicker overlay ─────────────────────────────────────────
  function overlay() {
    const d = document.createElement("div");
    d.className = "tg-overlay";
    document.body.appendChild(d);
  }

  // ── Arcade WebAudio SFX (synthesized; off by default) ──────────────────
  function sound() {
    let ac = null, master = null, padOn = false, enabled = false, lastBlip = 0;

    function ensure() {
      if (ac) return;
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      ac = new AC();
      master = ac.createGain();
      master.gain.value = 0.0;
      master.connect(ac.destination);
    }
    function blip(freq, dur, type) {
      if (!enabled || !ac) return;
      const now = ac.currentTime;
      if (now - lastBlip < 0.02) return;
      lastBlip = now;
      const o = ac.createOscillator(), g = ac.createGain();
      o.type = type || "square";
      o.frequency.value = freq;
      g.gain.setValueAtTime(0.0001, now);
      g.gain.exponentialRampToValueAtTime(0.16, now + 0.008);
      g.gain.exponentialRampToValueAtTime(0.0001, now + (dur || 0.12));
      o.connect(g); g.connect(master);
      o.start(now); o.stop(now + (dur || 0.12) + 0.02);
    }
    function victory() {
      if (!enabled || !ac) return;
      [523, 659, 784, 1047].forEach((f, i) => setTimeout(() => blip(f, 0.16, "triangle"), i * 90));
    }
    function startPad() {
      if (!ac || padOn) return;
      padOn = true;
      const pad = ac.createGain(); pad.gain.value = 0.05; pad.connect(master);
      const filt = ac.createBiquadFilter();
      filt.type = "lowpass"; filt.frequency.value = 700; filt.connect(pad);
      [110, 110.6, 165].forEach((f) => {
        const o = ac.createOscillator();
        o.type = "sawtooth"; o.frequency.value = f; o.connect(filt); o.start();
      });
      const lfo = ac.createOscillator(), lg = ac.createGain();
      lfo.frequency.value = 0.08; lg.gain.value = 260;
      lfo.connect(lg); lg.connect(filt.frequency); lfo.start();
    }
    function setEnabled(on) {
      ensure();
      if (!ac) return;
      enabled = on;
      if (ac.state === "suspended") ac.resume();
      if (on) {
        startPad();
        master.gain.setTargetAtTime(0.5, ac.currentTime, 0.2);
        victory();
      } else {
        master.gain.setTargetAtTime(0.0, ac.currentTime, 0.2);
      }
    }

    const btn = document.createElement("button");
    btn.className = "tg-sound-btn";
    btn.type = "button";
    btn.textContent = "♪ OFF";
    btn.setAttribute("aria-label", "Toggle arcade sound");
    btn.addEventListener("click", () => {
      const on = !enabled;
      setEnabled(on);
      btn.textContent = on ? "♪ ON" : "♪ OFF";
      btn.classList.toggle("on", on);
    });
    document.body.appendChild(btn);

    const hoverSel = "nav.top a, .btn, .cta, .agent-card, .lb-table tbody tr, .tg-sound-btn";
    document.addEventListener("pointerover", (e) => {
      const el = e.target.closest && e.target.closest(hoverSel);
      if (el) blip(420 + Math.random() * 80, 0.07, "square");
    });
    document.addEventListener("click", (e) => {
      const b = e.target.closest && e.target.closest(".btn, .cta");
      if (b) {
        blip(720, 0.12, "square");
        b.classList.add("tg-press");
        setTimeout(() => b.classList.remove("tg-press"), 240);
      }
    });
  }

  function init() { galaxy(); overlay(); sound(); }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
