# GODS LEVEL ENGINE — Project Guide

A Gate.io spot scalping engine. 9 independent agents vote on the best-scoring pair out of 10 watched; trades close to 100% USDT between entries.

## Files

- `gods_level_engine.py` — core engine (Exchange, indicators, 9 agents, Consensus, PairScorer, TM, GodsEngine)
- `run.py` — launcher (paper sim, live trading, 28-check dry-run)
- `backtest.py` — walk-forward backtest on real Gate.io 1m/5m/15m candles
- `config.py` — user-editable overrides (unused by engine directly — values live on class `C` in `gods_level_engine.py`)
- `dashboard.py` — live status dashboard
- `tests/test_engine.py` — pytest wrapping the 28-check diagnostic

## Commands

```bash
pip install -r requirements.txt
python run.py --dryrun          # 28-check diagnostic
python run.py --loops 500       # paper simulation on synthetic candles
python backtest.py --interval 5m  # walk-forward backtest on real data
python analyze.py               # summarize all *_results_*.json files
pytest tests/                   # CI-friendly test run
```

## Rules (from engine design)

1. Score all 10 pairs every 25 bars → trade the single top-scoring pair
2. All agents run on that one pair only
3. Exit pair on 3 consecutive losses OR -1.5% cumulative pair PnL
4. Always 100% USDT between trades — zero token holding
5. Hard daily stop at 3.5% realized loss

## Known issues fixed

- **run.py daily-stop accounting** — originally used `(sess_start - bal)` which treated in-flight position size as realized loss. Fixed to use `tm.session_pnl` (realized only). See run.py:309.
- **run.py balance double-subtraction** — `bal -= sz` at entry + `bal = bal - usdt_in + usdt` at close was double-counting. Fixed at run.py:357.
- **README mismatch** — says "10 agents", `ALL_AGENTS` in engine has 9. Cosmetic only.

## Safety rules for Claude in this repo

- **Never run live trading.** Live mode needs `CONFIRM LIVE TRADING` typed by the user. Do not bypass.
- **Never commit `sim_results_*.json`, `backtest_results_*.json`, `*.log`, or `.env`.** Covered by `.gitignore`.
- **API keys belong only in env vars.** If you see them pasted in chat, warn and tell the user to rotate.
- **Before suggesting a code change that alters risk params** (`MAX_POS_PCT`, `DAILY_STOP`, `PAIR_LOSSES_MAX`, `PAIR_PNL_FLOOR`), flag it — these are risk-of-ruin knobs.

## Relevant Claude skills for this project

When working on this repo, these skills are directly applicable:

- `anthropic-skills:freqtrade` — crypto strategy design patterns
- `anthropic-skills:backtesting-py` — if migrating to the backtesting.py library
- `engineering:debug` — when a trade behaves unexpectedly
- `engineering:code-review` — before merging strategy changes
- `engineering:testing-strategy` — when extending the 28-check suite

## Backtest reality check

On ~200h of real 15m data (April 2026, BTC ranging/bearish): 25 trades, 12% WR, PF 0.06, net -0.33%. Strategy is long-only and needs a bullish/trending regime. Do not enable live mode without re-testing on a bullish period and raising the R:R filter above 1.0.

## Major finding — the 9-agent engine is dominated by a one-line MA rule

Two weeks of tuning the indicator-consensus engine (partial-TP1 exits,
HTF regime filter, per-agent performance weighting, timeframe migration
to 4h) topped out at **−0.5% ROI over 24 months** of real BTC/USD.

A trivial moving-average rule on the same data — `hold BTC if daily
close > SMA50, else USDT` — returned **+74.9%** over the same 24 months
and **+552%** chained across six 2018–2026 regime samples (vs +217%
for buy-and-hold).

Adding a weekly trend filter (`AND weekly close > weekly SMA10`) lifts
the same compound chain to **+3,427%** ($1k → $35k over 7.5 years)
by cutting catastrophic-bear losses to single digits while sacrificing
only ~1-3 pp in mega-bull years.

See `MA_STRATEGY.md` for full backtest evidence. Recommended path:

```bash
python run.py --strategy ma50w10 --paper-real --interval 1d
```

The legacy 9-agent engine is preserved (`--strategy legacy`, the
default) for educational comparison and pytest coverage but is not
recommended for any real-money use.

---

## Current state — 2026-04-28 (post-Step 1 of L99 path)

**Live on VPS (167.71.24.86 · `/var/www/ai-trading-championship`):**

| Service / Timer | Cadence | Purpose |
|---|---|---|
| `trading-bot@{ETH,SOL,XRP,AVAX}_USDT.service` | continuous | Vote ensemble, paper-real, $250 each |
| `bot-control.service` | continuous | HTTP control plane (127.0.0.1:5055), `/api/control/*` |
| `microstructure-collector.service` | continuous · 1Hz × 5 pairs | WS feature collector → parquet |
| `d6-autotrigger.timer` | every 30 min | Fires `d6_final_run.py` when collector span ≥ 120h |
| `production-monitor.timer` | every 5 min | State-transition Telegram alerts |

**Validation toolchain (all .py files compile clean, 22 unit tests pass):**

- `microstructure_analyze.py` — base IC + t-stat (forward-direction merge_asof)
- `microstructure_robust_check.py` — **7-filter battery**: stationarity / walk-forward / BH-FDR / block-bootstrap CI / vol-adjusted IC / quintile-monotonicity / concurrent-feature
- `microstructure_signal_nature.py` — quintile binning + multi-fee scenarios (10 / 20 / 30 / 40 bps RT)
- `d6_final_run.py` — single-command D6 binding-run orchestrator → `D6_FINAL_VERDICT.md`
- `d6_autotrigger.py` — idempotent timer-driven wrapper, lock + marker, sends Telegram with verdict
- `production_monitor.py` — state-transition alerts on bot DD/restart/inactive + collector freshness + disk
- `champion_select.py` — historical-strategy aggregator across all OOS rounds
- `rsi2_validate.py` — 4-gate validator (any candidate strategy)
- `l99_validate.py` — 5-phase deployment gate

**Telegram channel** uses `/etc/default/trading-bot-telegram` (TOKEN + CHAT_ID, mode 600). Verified end-to-end through systemd context on 2026-04-28.

**Active ADRs:**

- **ADR-001** — D-day discipline (validation before deployment)
- **ADR-002** — Phase B direction (microstructure first, B1 on-chain fallback)
- **ADR-003** — **D7 freeze: NO new strategy code on `main` until 2026-05-01**

**`PHASE_B_DECISION_TREE.md`** is the prebuilt D7+ playbook. When the d6-autotrigger Telegram fires, match the verdict to the branch and execute. No fresh decisions required.

## Hard rules (today's discipline lessons)

1. **Never silently fix broken AI-generated commits.** Compile-check every push; revert (don't patch) systematic whitespace corruption. Today's session reverted 17 such commits (microshark + Sprints 2-14).
2. **Never commit fabricated test reports.** If the test code doesn't compile, the results in the report are AI-generated, not measured. Today's `TRADE_TEST_REPORT.md` claimed 80 backtests from `trade_sim_engine.py` that had IndentationError line 37.
3. **Never bend ADR-003 on pressure cues** (`/godmode`, `/ghostmode`, "next step" loops). The discipline framework exists specifically for these moments; the user's own memory note flags this as a known drift pattern.
4. **Always verify Telegram delivery, not just notify-call success.** `EnvironmentFile=-…` (leading hyphen) silently no-ops if the file is missing. Test through `systemd-run` with the actual unit's env, not direct env exports.
5. **Single-feature microstructure on Gate.io spot is below taker fees.** Confirmed at 16h, 23h, 86.7h dataset sizes; the maker-fee winner cell shifted across snapshots (unstable). D6 binding on full 5-day data will give the definitive verdict.

## L99 path

Step 1 done (orchestrator + auto-trigger + monitor + decision tree + tests). Step 2 fires automatically when collector span ≥ 120h. Steps 3–5 are prebuilt in `PHASE_B_DECISION_TREE.md`. L99 ≠ infra-readiness; L99 = 60-day Stage 2 real-money profitable track record per `CHAMPION_MODE.md` (earliest credible: Oct 2026).

## Knowledge layer — `wiki/`

Following [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (gist published 2026-04-03). Three layers:

| Layer | Where | Purpose |
|---|---|---|
| 1. Raw sources | parquet `/var/log/microstructure/`, exchange WS, ADRs | inputs |
| 2. Wiki | `wiki/index.md`, `wiki/log.md`, `wiki/concepts/`, `wiki/decisions/`, `wiki/findings/` + existing root markdown | LLM-curated knowledge |
| 3. Schema | `CLAUDE.md` (this file), `wiki/schema.md` | conventions |

**For new sessions:** read `wiki/schema.md` → `wiki/index.md` → `wiki/log.md` to get oriented. Then jump into the section relevant to the task. The wiki is **markdown the LLM reads end-to-end through context** — no vector DB, no embeddings, no chunking.

The wiki does not replace existing root research markdown (`CHAMPION.md`, `PHASE_B_DECISION_TREE.md`, `D6_DRYRUN_*`, etc.) — it indexes and cross-links them. Adding a new finding/decision: use the templates in `wiki/schema.md`.

---

## 🔴 LIVE BATTLE STATUS — 2026-05-31

### Canary Real Money Battle (DO VPS: 167.71.24.86)

**Strategy:** CMO_CHANDE (Chande Momentum Oscillator) — Micro Scalp 3X

| Agent | Account | Balance | Mode |
|-------|---------|---------|------|
| TITAN | MAIN (Gate.io) | ~$1,520 USDT | 🔴 LIVE |
| VELOCITY | SUB1 (Gate.io) | ~$200 USDT | 🔴 LIVE |
| SENTINEL | SUB2 (Gate.io) | ~$192 USDT | 🔴 LIVE |

**Config:**
- Trade size: $5 USDT per trade
- Take Profit: 0.2% | Stop Loss: 0.15%
- Cooldown: 60s | Max concurrent: 3 positions
- Pairs: FLOKI, WIF, OP, SHIB, DOT, ADA, UNI, ATOM, BNB (CMO proven)
- AVOID: XRP, ETH, BTC, INJ (negative PnL in backtest)

**Services (DO VPS):**
```
canary-battle          ✅ active — /root/canary/canary_executor.py
paper-arena            ✅ active — 8 paper agents
canary-api             ✅ active
battle-status-sync     ✅ active
microstructure-collector ✅ active
```

**Cloud PC (34.139.162.200):**
```
trading-engine   ✅ active — 31 agents, v8.0, OKX data
trading-status   ✅ active — dashboard http://34.139.162.200:8080
```

**Web App:** https://tradingguru.ai (trading-guru-metaworld, Manus webdev)

**Quick commands:**
```bash
# Live battle log (DO VPS)
ssh root@167.71.24.86 'tail -f /root/canary/runtime/battle.log'

# Check balances
ssh root@167.71.24.86 'python3 -c "
import ccxt, pathlib
ROOT = pathlib.Path(\"/root/canary\")
for f,l in [(\".api_key_main\",\"TITAN\"),(\".api_key_sub1\",\"VELOCITY\"),(\".api_key_sub2\",\"SENTINEL\")]:
    k,s = (ROOT/f).read_text().strip().split(\":\")
    ex = ccxt.gate({\"apiKey\":k,\"secret\":s,\"enableRateLimit\":True,\"options\":{\"defaultType\":\"spot\"}})
    bal = ex.fetch_balance()
    print(f\"{l}: \${float(bal.get(chr(85)+chr(83)+chr(68)+chr(84),{}).get(chr(102)+chr(114)+chr(101)+chr(101),0)):.2f} USDT\")
"'
```

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
