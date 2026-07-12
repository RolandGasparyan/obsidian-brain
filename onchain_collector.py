#!/usr/bin/env python3
"""
onchain_collector.py — B1 fallback data collector.

Polls free-tier on-chain APIs every 5 minutes, computes engineered
features (z-scored where appropriate), writes parquet hourly to
/var/log/onchain/YYYY-MM-DD/HH/{pair}.parquet

Schema mirrors microstructure_collector.py output so the existing
7-filter battery (microstructure_robust_check.py), signal-nature
quintile (microstructure_signal_nature.py), and Bayesian sweep
(bayesian_edge_sweep.py) work UNCHANGED on the new data class.

Triggered by D6 BINDING NO-GO + PHASE_B_DECISION_TREE.md branch B.2.3.

DATA SOURCES (all free tier, $0/month pre-validation)
─────────────────────────────────────────────────────
  CryptoQuant    /v1/btc/exchange-flows/netflow
                 /v1/btc/miner-flows/outflow
                 (free metrics, generous limits)
  Glassnode      /v1/metrics/market/mvrv  (BTC/ETH)
                 /v1/metrics/indicators/sopr
                 /v1/metrics/indicators/nvt
                 (free tier exposes basic charts via API)
  Whale Alert    /v1/transactions
                 (10 req/min free, 30-day history, $1M+ default)

ENV VARS (set on VPS via /etc/default/onchain-collector — created at deploy)
─────────────────────────────────────────────────
  CRYPTOQUANT_API_KEY  (free tier key)
  GLASSNODE_API_KEY    (free tier key)
  WHALE_ALERT_API_KEY  (free tier key)

If any key is missing, that source is silently skipped (mirror the
telegram_alerts.py pattern). Collector keeps running on the others.

CADENCE
──────
  Per-source poll interval: 5 minutes (these signals move on hours-days)
  Hourly parquet flush

FEATURES PRODUCED (per pair, per snapshot)
──────────────────────────────────────────
  ts_ms                 unix timestamp (ms)
  pair                  BTC_USDT / ETH_USDT etc.

  exchange_netflow      from CryptoQuant
  exchange_netflow_z30  rolling 30-day z-score
  miner_outflow         from CryptoQuant
  miner_outflow_z30     rolling 30-day z-score

  mvrv                  Glassnode (raw value)
  sopr                  Glassnode (raw value)
  nvt                   Glassnode (raw value)

  whale_tx_count_1h     count of >$1M txs last 60 min
  whale_tx_volume_1h    sum USD volume of >$1M txs last 60 min
  whale_tx_to_exchange  count of large txs going INTO known exchanges
  whale_tx_from_exchange count going OUT (HODL signal)

  api_lag_cryptoquant_ms   how stale the data was when fetched
  api_lag_glassnode_ms     ditto
  api_lag_whale_alert_ms   ditto

PARQUET PATH
────────────
  /var/log/onchain/YYYY-MM-DD/HH/{pair}.parquet

Same hierarchy as microstructure_collector → same downstream tools work.

ADR
───
  ADR-003 expired 2026-05-01 ~00:00 UTC. New strategy/data code on
  feat/b1-onchain-research; will merge to main after PR review.

Usage
─────
  systemctl: install systemd/onchain-collector.service (provided)
  manual:    python onchain_collector.py --pairs BTC_USDT ETH_USDT
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import math
import os
import signal
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

try:
    import pandas as pd
    import requests
except ImportError:
    print("pip install pandas requests pyarrow", file=sys.stderr)
    sys.exit(1)


# ── configuration ─────────────────────────────────────────────────────
DEFAULT_PAIRS = ["BTC_USDT", "ETH_USDT"]   # B1 starts with the two largest
POLL_INTERVAL_SEC = 300                     # 5 min — slow on-chain signals
WHALE_TX_WINDOW_SEC = 3600                  # rolling 1h window for whale tx aggregation
PARQUET_FLUSH_INTERVAL_SEC = 3600           # hourly flush

CRYPTOQUANT_BASE = "https://api.cryptoquant.com/v1"
GLASSNODE_BASE = "https://api.glassnode.com/v1"
WHALE_ALERT_BASE = "https://api.whale-alert.io/v1"

CRYPTOQUANT_KEY = os.environ.get("CRYPTOQUANT_API_KEY", "").strip()
GLASSNODE_KEY = os.environ.get("GLASSNODE_API_KEY", "").strip()
WHALE_ALERT_KEY = os.environ.get("WHALE_ALERT_API_KEY", "").strip()

# Coin Metrics-style asset name mapping
PAIR_TO_ASSET = {
    "BTC_USDT": "btc",
    "ETH_USDT": "eth",
}


# ── per-source clients ────────────────────────────────────────────────
def _http_get(url: str, params: Dict[str, Any], timeout: float = 10.0,
              api_key_header: Optional[Tuple[str, str]] = None) -> Tuple[Optional[Dict[str, Any]], int]:
    """Returns (json_or_None, latency_ms). Errors return (None, latency_ms)."""
    headers: Dict[str, str] = {}
    if api_key_header:
        headers[api_key_header[0]] = api_key_header[1]
    t0 = time.time()
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        lag_ms = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            return None, lag_ms
        return r.json(), lag_ms
    except Exception:
        return None, int((time.time() - t0) * 1000)


def cryptoquant_exchange_netflow(asset: str) -> Tuple[Optional[float], int]:
    if not CRYPTOQUANT_KEY:
        return None, 0
    url = f"{CRYPTOQUANT_BASE}/{asset}/exchange-flows/netflow"
    params = {"window": "hour", "limit": 1}
    data, lag = _http_get(url, params,
                            api_key_header=("Authorization", f"Bearer {CRYPTOQUANT_KEY}"))
    if not data or "result" not in data:
        return None, lag
    rows = data["result"].get("data", [])
    if not rows:
        return None, lag
    val = rows[0].get("netflow_total")
    return (float(val) if val is not None else None), lag


def cryptoquant_miner_outflow(asset: str) -> Tuple[Optional[float], int]:
    if not CRYPTOQUANT_KEY:
        return None, 0
    url = f"{CRYPTOQUANT_BASE}/{asset}/miner-flows/outflow"
    params = {"window": "hour", "limit": 1}
    data, lag = _http_get(url, params,
                            api_key_header=("Authorization", f"Bearer {CRYPTOQUANT_KEY}"))
    if not data or "result" not in data:
        return None, lag
    rows = data["result"].get("data", [])
    if not rows:
        return None, lag
    val = rows[0].get("outflow_total")
    return (float(val) if val is not None else None), lag


def glassnode_metric(metric_path: str, asset: str) -> Tuple[Optional[float], int]:
    """metric_path e.g. 'market/mvrv', 'indicators/sopr', 'indicators/nvt'."""
    if not GLASSNODE_KEY:
        return None, 0
    url = f"{GLASSNODE_BASE}/metrics/{metric_path}"
    params = {"a": asset.upper(), "i": "1h", "api_key": GLASSNODE_KEY}
    data, lag = _http_get(url, params)
    if not data or not isinstance(data, list) or not data:
        return None, lag
    last = data[-1]
    val = last.get("v")
    return (float(val) if val is not None else None), lag


def whale_alert_recent_txs(window_sec: int = 3600) -> Tuple[List[Dict[str, Any]], int]:
    """Returns list of recent large-transaction dicts within window."""
    if not WHALE_ALERT_KEY:
        return [], 0
    now_s = int(time.time())
    url = f"{WHALE_ALERT_BASE}/transactions"
    params = {
        "api_key": WHALE_ALERT_KEY,
        "start": now_s - window_sec,
        "end": now_s,
        "limit": 100,
    }
    data, lag = _http_get(url, params)
    if not data or "transactions" not in data:
        return [], lag
    return data["transactions"], lag


# ── feature aggregation ──────────────────────────────────────────────
@dataclass
class WhaleTxBuffer:
    """Rolling 1h window of large transactions per asset."""
    txs: Deque[Tuple[int, str, float, str, str]] = field(default_factory=deque)
    # (ts_s, symbol, amount_usd, from_owner_type, to_owner_type)

    def add(self, ts_s: int, symbol: str, amount_usd: float,
            from_owner: str, to_owner: str) -> None:
        self.txs.append((ts_s, symbol, amount_usd, from_owner, to_owner))
        cutoff = ts_s - WHALE_TX_WINDOW_SEC
        while self.txs and self.txs[0][0] < cutoff:
            self.txs.popleft()

    def stats_for_symbol(self, symbol: str, now_s: int) -> Dict[str, float]:
        cutoff = now_s - WHALE_TX_WINDOW_SEC
        while self.txs and self.txs[0][0] < cutoff:
            self.txs.popleft()
        relevant = [t for t in self.txs if t[1].lower() == symbol.lower()]
        count = len(relevant)
        volume = sum(t[2] for t in relevant)
        to_exch = sum(1 for t in relevant if t[4] == "exchange")
        from_exch = sum(1 for t in relevant if t[3] == "exchange")
        return {
            "whale_tx_count_1h": float(count),
            "whale_tx_volume_1h": float(volume),
            "whale_tx_to_exchange": float(to_exch),
            "whale_tx_from_exchange": float(from_exch),
        }


@dataclass
class FlowZScorer:
    """30-day rolling z-score for flow-style metrics.

    Buffers samples, computes z = (x - mean) / std over trailing window.
    """
    window_sec: int = 30 * 24 * 3600
    samples: Deque[Tuple[int, float]] = field(default_factory=deque)

    def push(self, ts_s: int, value: float) -> Optional[float]:
        self.samples.append((ts_s, value))
        cutoff = ts_s - self.window_sec
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()
        if len(self.samples) < 10:
            return None     # need a minimum sample to z-score
        vals = [v for _, v in self.samples]
        mu = sum(vals) / len(vals)
        var = sum((v - mu) ** 2 for v in vals) / max(1, len(vals) - 1)
        sd = math.sqrt(var)
        if sd == 0:
            return 0.0
        return (value - mu) / sd


@dataclass
class PairState:
    pair: str
    asset: str
    netflow_z: FlowZScorer = field(default_factory=FlowZScorer)
    miner_z: FlowZScorer = field(default_factory=FlowZScorer)
    buffer: List[Dict[str, Any]] = field(default_factory=list)


# ── snapshot loop ────────────────────────────────────────────────────
def take_snapshot(state: PairState, whale_buffer: WhaleTxBuffer,
                   log: logging.Logger) -> Dict[str, Any]:
    now_s = int(time.time())
    ts_ms = now_s * 1000

    # CryptoQuant
    netflow, lag_cq = cryptoquant_exchange_netflow(state.asset)
    miner, _ = cryptoquant_miner_outflow(state.asset)
    netflow_z = state.netflow_z.push(now_s, netflow) if netflow is not None else None
    miner_z = state.miner_z.push(now_s, miner) if miner is not None else None

    # Glassnode
    mvrv, lag_gn = glassnode_metric("market/mvrv", state.asset)
    sopr, _ = glassnode_metric("indicators/sopr", state.asset)
    nvt, _ = glassnode_metric("indicators/nvt", state.asset)

    # Whale Alert (refreshed once per snapshot, shared across pairs)
    whale_stats = whale_buffer.stats_for_symbol(state.asset, now_s)

    snap = {
        "ts_ms": ts_ms,
        "pair": state.pair,
        "asset": state.asset,
        # CryptoQuant
        "exchange_netflow": netflow if netflow is not None else float("nan"),
        "exchange_netflow_z30": netflow_z if netflow_z is not None else float("nan"),
        "miner_outflow": miner if miner is not None else float("nan"),
        "miner_outflow_z30": miner_z if miner_z is not None else float("nan"),
        # Glassnode
        "mvrv": mvrv if mvrv is not None else float("nan"),
        "sopr": sopr if sopr is not None else float("nan"),
        "nvt": nvt if nvt is not None else float("nan"),
        # Whale Alert (rolling 1h)
        **whale_stats,
        # API lag
        "api_lag_cryptoquant_ms": float(lag_cq),
        "api_lag_glassnode_ms": float(lag_gn),
    }
    return snap


def refresh_whale_buffer(buf: WhaleTxBuffer, log: logging.Logger) -> int:
    """Pull recent whale txs into the rolling buffer. Returns api lag ms."""
    txs, lag_ms = whale_alert_recent_txs(WHALE_TX_WINDOW_SEC)
    for tx in txs:
        ts = int(tx.get("timestamp", 0))
        symbol = tx.get("symbol", "")
        amount_usd = float(tx.get("amount_usd", 0))
        from_owner = tx.get("from", {}).get("owner_type", "unknown")
        to_owner = tx.get("to", {}).get("owner_type", "unknown")
        # only keep new ones
        if any(x[0] == ts and x[1] == symbol and x[2] == amount_usd for x in buf.txs):
            continue
        buf.add(ts, symbol, amount_usd, from_owner, to_owner)
    return lag_ms


# ── parquet flush ────────────────────────────────────────────────────
def _hour_stamp() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d/%H")


def flush_all(states: Dict[str, PairState], out_dir: Path,
              hour_stamp: str, log: logging.Logger) -> None:
    hr_dir = out_dir / hour_stamp
    hr_dir.mkdir(parents=True, exist_ok=True)
    for pair, st in states.items():
        if not st.buffer:
            continue
        df = pd.DataFrame(st.buffer)
        df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
        out_path = hr_dir / f"{pair}.parquet"
        if out_path.exists():
            old = pd.read_parquet(out_path)
            df = pd.concat([old, df], ignore_index=True)
            df = df.sort_values("ts_ms").drop_duplicates("ts_ms")
        df.to_parquet(out_path, compression="zstd", index=False)
        log.info(f"flushed {pair}: +{len(st.buffer)} rows → {out_path} (total {len(df)})")
        st.buffer.clear()


# ── main loop ────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=DEFAULT_PAIRS)
    ap.add_argument("--out-dir", default="/var/log/onchain")
    ap.add_argument("--poll-sec", type=int, default=POLL_INTERVAL_SEC)
    ap.add_argument("--once", action="store_true",
                    help="take one snapshot and exit (smoke test)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)-5s | %(message)s")
    log = logging.getLogger("onchain")

    # Sanity: are any keys configured?
    sources = []
    if CRYPTOQUANT_KEY: sources.append("CryptoQuant")
    if GLASSNODE_KEY:   sources.append("Glassnode")
    if WHALE_ALERT_KEY: sources.append("WhaleAlert")
    if not sources:
        log.error("No API keys configured. Set CRYPTOQUANT_API_KEY, "
                   "GLASSNODE_API_KEY, WHALE_ALERT_API_KEY (any subset).")
        return 2
    log.info(f"sources active: {', '.join(sources)}")
    log.info(f"poll: every {args.poll_sec}s · pairs: {args.pairs}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Per-pair state
    states: Dict[str, PairState] = {}
    for pair in args.pairs:
        asset = PAIR_TO_ASSET.get(pair)
        if not asset:
            log.warning(f"pair {pair} has no asset mapping; skipping")
            continue
        states[pair] = PairState(pair=pair, asset=asset)

    whale_buffer = WhaleTxBuffer()
    last_flush_hour = _hour_stamp()

    # Graceful shutdown
    stop = False
    def _on_term(*_): nonlocal_setter()
    def nonlocal_setter():
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, _on_term)
    signal.signal(signal.SIGINT, _on_term)

    while not stop:
        # Refresh whale buffer once per cycle (shared across pairs)
        if WHALE_ALERT_KEY:
            refresh_whale_buffer(whale_buffer, log)

        # Snapshot each pair
        for pair, state in states.items():
            try:
                snap = take_snapshot(state, whale_buffer, log)
                state.buffer.append(snap)
                # quick visibility log
                fields = []
                for k in ("mvrv", "sopr", "nvt", "exchange_netflow_z30"):
                    v = snap.get(k)
                    if v is not None and not (isinstance(v, float) and math.isnan(v)):
                        fields.append(f"{k}={v:.3f}")
                log.info(f"snap {pair}  " + "  ".join(fields) if fields else
                         f"snap {pair}  (all features nan; check API keys)")
            except Exception as e:
                log.error(f"{pair} snapshot error: {e}")

        # Hourly flush
        hr = _hour_stamp()
        if hr != last_flush_hour:
            flush_all(states, out_dir, last_flush_hour, log)
            last_flush_hour = hr

        if args.once:
            flush_all(states, out_dir, last_flush_hour, log)
            log.info("--once mode: exiting")
            return 0

        # Sleep until next poll
        for _ in range(args.poll_sec):
            if stop: break
            time.sleep(1)

    # Final flush on shutdown
    flush_all(states, out_dir, last_flush_hour, log)
    log.info("shutdown clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
