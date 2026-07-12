import time
import pandas as pd
import numpy as np

from tournament.brain import TournamentBrain
from tournament.champion_momentum_engine import CandidateFeatures
from tournament.usdt_domination_core import TradeEvent

PAIR = "BTC_USDT"
INTERVAL = "15m"
CSV_PATH = "./calib_15m/BTC_USDT_15m_90d.csv"

STARTING_USDT = 3800.0

brain = TournamentBrain(starting_usdt=STARTING_USDT)

df = pd.read_csv(CSV_PATH)

open_positions = 0
realized_today = 0.0

print("=== LIVE BRAIN TEST MODE ===")

for i in range(100, len(df)):

    window = df.iloc[:i]
    current = window.iloc[-1]

    ohlcv = {
        "high": window["high"].values,
        "low": window["low"].values,
        "close": window["close"].values,
        "volume": window["volume"].values,
    }

    features = CandidateFeatures(
        pair=PAIR,
        roc_pct=0.0,
        ema_stack_score=0.5,
        rsi=50.0,
        rel_volume=1.0,
        regime_fit=0.5,
        taker_buy_ratio=0.5,
        book_imbalance=0.0,
        cvd_slope_z=0.0,
        ml_long_prob=0.5,
        atr_pct=0.5,
        proposed_rr=2.0,
    )

    decision = brain.evaluate_entry(
        features=features,
        ohlcv=ohlcv,
        open_positions=open_positions,
        realized_pnl_today_usdt=realized_today,
    )

    if decision.allow:
        print(f"[ENTRY] Score={decision.composite_score:.2f} RiskMult={decision.recommended_risk_multiplier}")
        open_positions = 1

        pnl = 50.0  # simulated profit
        event = TradeEvent(
            pair=PAIR,
            realized_pnl_usdt=pnl,
            r_multiple=1.0,
            duration_seconds=900,
            timestamp=time.time()
        )

        brain.on_trade_closed(event)
        open_positions = 0
        realized_today += pnl

    time.sleep(0.01)

print("=== DONE ===")
