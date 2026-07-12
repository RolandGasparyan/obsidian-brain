"""
l99.config — unified configuration for all three engines.

ONE place where every engine looks up: starting equity, fee tiers,
engine allocations per stage, data paths, polling cadences. Anything
hard-coded in two engines is a bug — it goes here.

This is configuration ONLY. No business logic, no IO, no exchange
clients. Engines import what they need.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict


# ── canonical engine identifiers ─────────────────────────────────────
class EngineId(str, Enum):
    GODMODE  = "godmode"          # futures microstructure
    AEGIS    = "aegis_alpha"       # spot momentum rotation
    PREDATOR = "quant_predator"    # MTF position trades


# ── fee tiers (Gate.io VIP 0 — verify on your account) ──────────────
@dataclass(frozen=True)
class FeeTier:
    futures_maker_pct:  float
    futures_taker_pct:  float
    spot_maker_pct:     float
    spot_taker_pct:     float
    estimated_slip_pct: float


GATE_VIP0 = FeeTier(
    futures_maker_pct=0.0002,    # 0.02% — third-party VIP0 estimate
    futures_taker_pct=0.0005,    # 0.05%
    spot_maker_pct=0.0010,       # 0.10%
    spot_taker_pct=0.0015,       # 0.15%
    estimated_slip_pct=0.0003,   # 3bp average slip on taker exits
)


# ── repo + data paths ───────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = REPO_ROOT / ".l99_data"          # gitignored


@dataclass(frozen=True)
class EnginePaths:
    journal:         Path
    decisions:       Path
    snapshot:        Path
    open_positions:  Path

    @classmethod
    def for_engine(cls, eid: EngineId) -> "EnginePaths":
        base = DATA_ROOT / eid.value
        base.mkdir(parents=True, exist_ok=True)
        return cls(
            journal        = base / "journal.jsonl",
            decisions      = base / "decisions.jsonl",
            snapshot       = base / "snapshot.json",
            open_positions = base / "open_positions.json",
        )


# ── unified config object (single source of truth) ──────────────────
@dataclass(frozen=True)
class L99Config:
    # Starting equity per CHAMPION_MODE.md §1.1 ($3k → $1M).
    # Override via env L99_STARTING_EQUITY.
    starting_equity:      float = float(os.getenv("L99_STARTING_EQUITY", "3000.0"))

    # Default contract / pair universes
    futures_contract:     str   = "BTC_USDT"
    spot_universe_top_n:  int   = 50              # legacy default (4H)
    spot_universe_top_n_4h: int = 75              # PLAN B: expanded 4H universe
    spot_universe_top_n_1h: int = 100             # PLAN B: 1H wide net
    btc_ref_pair:         str   = "BTC_USDT"

    # Polling cadences (seconds)
    alpha_scan_interval_s:       int = 4 * 3600    # 4h cadence
    alpha_1h_scan_interval_s:    int = 1 * 3600    # PLAN B: 1h cadence
    predator_scan_interval_s:    int = 24 * 3600    # daily
    btc_vol_refresh_s:           int = 6 * 3600     # 6h
    journal_flush_s:             int = 30           # disk flush every 30s

    # ── PLAN B: Dual-Timeframe Acceleration ─────────────────────────
    # 4H + 1H aegis run in parallel under shared exposure cap.
    # Doctrine §VI viability is evaluated SEPARATELY per timeframe;
    # each timeframe earns capital independently.
    global_max_open_risk_pct:   float = 0.06       # 6% portfolio cap
    alpha_4h_max_open_risk_pct: float = 0.02       # 4H slice
    alpha_1h_max_open_risk_pct: float = 0.02       # 1H slice (2% buffer remaining)

    # Telegram (read from env at engine startup; not stored)
    telegram_bot_token_env:  str = "TELEGRAM_BOT_TOKEN"
    telegram_chat_id_env:    str = "TELEGRAM_CHAT_ID"

    # Champion gates
    statistical_viability_min_trades: int = 50      # before any auto-shutdown decision

    # Engine activation flags (env-overridable for paper deploys)
    enable_godmode:   bool = os.getenv("L99_ENABLE_GODMODE",   "1") == "1"
    enable_aegis:     bool = os.getenv("L99_ENABLE_AEGIS",     "1") == "1"
    enable_predator:  bool = os.getenv("L99_ENABLE_PREDATOR",  "0") == "1"

    fees:             FeeTier = GATE_VIP0

    # Per-stage capital allocation across engines (§2.2)
    # Stage 1: godmode 40%, aegis 40%, predator 20%
    # Stage 4: godmode 10%, aegis 30%, predator 60%
    _allocations: Dict[int, Dict[str, float]] = field(default_factory=lambda: {
        1: {EngineId.GODMODE.value: 0.40, EngineId.AEGIS.value: 0.40,
            EngineId.PREDATOR.value: 0.20},
        2: {EngineId.GODMODE.value: 0.30, EngineId.AEGIS.value: 0.40,
            EngineId.PREDATOR.value: 0.30},
        3: {EngineId.GODMODE.value: 0.20, EngineId.AEGIS.value: 0.35,
            EngineId.PREDATOR.value: 0.45},
        4: {EngineId.GODMODE.value: 0.10, EngineId.AEGIS.value: 0.30,
            EngineId.PREDATOR.value: 0.60},
    })

    def allocation(self, stage: int) -> Dict[str, float]:
        """Return engine → fraction-of-equity map for the given stage."""
        if stage < 1: stage = 1
        if stage > 4: stage = 4
        return dict(self._allocations[stage])

    def is_engine_enabled(self, eid: EngineId) -> bool:
        return {
            EngineId.GODMODE:  self.enable_godmode,
            EngineId.AEGIS:    self.enable_aegis,
            EngineId.PREDATOR: self.enable_predator,
        }[eid]


CONFIG = L99Config()
