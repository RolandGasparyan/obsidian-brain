#!/usr/bin/env python3
"""
Trading Strategies Testing Engine v7.0
20 Strategies × 9 Trading Modes × 5 Risk Personalities × 29 Tokens
All agents practicing, learning, and self-upgrading 24/7
"""

import asyncio
import json
import sqlite3
import time
import random
import math
import logging
import os
from datetime import datetime, timezone
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import ccxt

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
VERSION = "v9.2"
TICK_INTERVAL = 5          # seconds between ticks
MIN_HISTORY   = 12         # ticks before agents can trade
GURU_LEARN_EVERY = 10      # ticks between Guru self-learning cycles
STATE_SAVE_EVERY = 20      # ticks between state snapshots
RISK_ADAPT_EVERY = 25      # ticks between risk mode adaptation
COLD_WALLET_THRESHOLD = 100.0
RISK_PER_TRADE = 0.02
STARTING_CAPITAL = 1000.0
MAX_OPEN_PER_AGENT = 8     # increased for multi-token coverage
REPROBE_EVERY = 500        # re-probe OKX tokens every N ticks
MAX_RETRIES = 5            # max API retry attempts
RETRY_DELAY = 3            # seconds between retries

# ── HARD CONSTRAINT (project rule): SHORT-ONLY ───────────────────────────────
# Project policy bans LONG trades for every agent including TRADING GURU.
# These globals enforce it across signal filtering, mode selection, SL/TP
# rebalancing and Guru self-learning. Do NOT flip without explicit approval.
SHORT_ONLY = True
TP_SL_RATIO = 2.5          # TP target multiplier vs SL (was effectively ~1.0)
MIN_PRICE_FLOOR = 1e-9     # treat anything <= this as offline / no fetch

BASE_DIR = "/home/ubuntu/trading_engine"
DB_PATH  = os.path.join(BASE_DIR, "trades.db")
LOG_PATH = os.path.join(BASE_DIR, "engine.log")
STATE_PATH = os.path.join(BASE_DIR, "engine_state_v8.json")
KB_PATH  = os.path.join(BASE_DIR, "knowledge_base.json")

# ─────────────────────────────────────────────
# 29-TOKEN UNIVERSE (4 TIERS)
# ─────────────────────────────────────────────
TOKENS = {
    "TIER1_MAJOR":  ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT"],
    "TIER2_MIDCAP": ["AVAX/USDT", "LINK/USDT", "DOT/USDT", "ADA/USDT", "MATIC/USDT",
                     "ATOM/USDT", "UNI/USDT", "LTC/USDT", "NEAR/USDT", "APT/USDT"],
    "TIER3_ALT":    ["DOGE/USDT", "SHIB/USDT", "ARB/USDT", "OP/USDT", "INJ/USDT",
                     "SUI/USDT", "TIA/USDT", "SEI/USDT", "WLD/USDT"],
    "TIER4_MEME":   ["PEPE/USDT", "FLOKI/USDT", "BONK/USDT", "WIF/USDT", "BOME/USDT"],
}
ALL_TOKENS = [t for tier in TOKENS.values() for t in tier]

# Per-token ATR volatility calibration (% of price)
TOKEN_ATR = {
    "BTC/USDT": 0.004, "ETH/USDT": 0.005, "SOL/USDT": 0.007, "XRP/USDT": 0.008,
    "BNB/USDT": 0.005, "AVAX/USDT": 0.009, "LINK/USDT": 0.010, "DOT/USDT": 0.010,
    "ADA/USDT": 0.009, "MATIC/USDT": 0.011, "ATOM/USDT": 0.010, "UNI/USDT": 0.011,
    "LTC/USDT": 0.007, "NEAR/USDT": 0.012, "APT/USDT": 0.013, "DOGE/USDT": 0.012,
    "SHIB/USDT": 0.015, "ARB/USDT": 0.013, "OP/USDT": 0.013, "INJ/USDT": 0.014,
    "SUI/USDT": 0.014, "TIA/USDT": 0.015, "SEI/USDT": 0.015, "WLD/USDT": 0.014,
    "PEPE/USDT": 0.020, "FLOKI/USDT": 0.020, "BONK/USDT": 0.020, "WIF/USDT": 0.018,
    "BOME/USDT": 0.020,
}

# ─────────────────────────────────────────────
# 20 TRADING STRATEGIES
# ─────────────────────────────────────────────
STRATEGIES = {
    # ── ORIGINAL 8 ──────────────────────────────────────────────────────
    "EMA_CROSSOVER":        {"name": "EMA 9/21 Crossover",          "min_hist": 21, "modes": ["SCALP_SHORT","SCALP_LONG"]},
    "VWAP_MACD":            {"name": "VWAP + MACD Momentum",         "min_hist": 20, "modes": ["SCALP_SHORT","SWING_SHORT"]},
    "KELTNER_RSI":          {"name": "Keltner Channel + RSI",        "min_hist": 20, "modes": ["MEAN_REVERSION"]},
    "BB_SQUEEZE":           {"name": "Bollinger Band Squeeze",       "min_hist": 20, "modes": ["BREAKOUT_SHORT","BREAKOUT_LONG"]},
    "SUPERTREND_MACD":      {"name": "SuperTrend + MACD",            "min_hist": 20, "modes": ["MOMENTUM_SHORT","SWING_SHORT"]},
    "ORDER_FLOW":           {"name": "Order Flow Imbalance",         "min_hist": 15, "modes": ["SCALP_SHORT","GRID"]},
    "PIVOT_BREAKDOWN":      {"name": "Pivot Point Breakdown",        "min_hist": 15, "modes": ["BREAKOUT_SHORT","BREAKOUT_LONG"]},
    "ALMA_STOCH":           {"name": "ALMA + Stochastic Reversal",   "min_hist": 20, "modes": ["MEAN_REVERSION","GRID"]},
    # ── NEW 12 ──────────────────────────────────────────────────────────
    "RANGE_TRADING":        {"name": "Range Trading S/R",            "min_hist": 20, "modes": ["MEAN_REVERSION","GRID"]},
    "PRICE_ACTION":         {"name": "Price Action Candlestick",     "min_hist": 10, "modes": ["SCALP_SHORT","SCALP_LONG","BREAKOUT_LONG"]},
    "PULLBACK_MOMENTUM":    {"name": "Pullback Momentum (50-EMA)",   "min_hist": 50, "modes": ["SWING_LONG","SWING_SHORT","MOMENTUM_LONG"]},
    "BREAKOUT_VOLUME":      {"name": "Breakout + Volume Confirm",    "min_hist": 20, "modes": ["BREAKOUT_LONG","BREAKOUT_SHORT"]},
    "RSI_DIVERGENCE":       {"name": "RSI Divergence",               "min_hist": 20, "modes": ["MEAN_REVERSION","SCALP_SHORT"]},
    "ICHIMOKU_CLOUD":       {"name": "Ichimoku Cloud Breakout",      "min_hist": 52, "modes": ["SWING_LONG","SWING_SHORT"]},
    "FIBONACCI_RETRACEMENT":{"name": "Fibonacci Retracement",        "min_hist": 30, "modes": ["MEAN_REVERSION","SWING_LONG"]},
    "HEIKIN_ASHI_TREND":    {"name": "Heikin Ashi Trend Filter",     "min_hist": 15, "modes": ["MOMENTUM_LONG","MOMENTUM_SHORT"]},
    "WILLIAMS_R_REVERSAL":  {"name": "Williams %R Reversal",         "min_hist": 14, "modes": ["MEAN_REVERSION","SCALP_LONG"]},
    "ADX_TREND_STRENGTH":   {"name": "ADX Trend Strength Filter",    "min_hist": 20, "modes": ["MOMENTUM_LONG","MOMENTUM_SHORT","SWING_LONG"]},
    "PARABOLIC_SAR":        {"name": "Parabolic SAR Flip",           "min_hist": 15, "modes": ["SCALP_SHORT","SCALP_LONG","MOMENTUM_SHORT"]},
    "TRIPLE_EMA":           {"name": "Triple EMA (5/13/34)",         "min_hist": 34, "modes": ["MOMENTUM_LONG","MOMENTUM_SHORT","SCALP_LONG"]},
    # ── NEW 10 (Deep Research) ──────────────────────────────────────────
    "DONCHIAN_BREAKOUT":    {"name": "Donchian Channel Breakout",    "min_hist": 20, "modes": ["BREAKOUT_SHORT"]},
    "LAGUERRE_RSI":         {"name": "Laguerre RSI Pullback",        "min_hist": 15, "modes": ["MEAN_REVERSION","SCALP_SHORT"]},
    "SQUEEZE_MOMENTUM":     {"name": "Squeeze Momentum (LazyBear)",  "min_hist": 20, "modes": ["MOMENTUM_SHORT","BREAKOUT_SHORT"]},
    "FAIR_VALUE_GAP":       {"name": "ICT Fair Value Gap (FVG)",     "min_hist": 10, "modes": ["MEAN_REVERSION","SCALP_SHORT"]},
    "ORDER_BLOCK_LIQ":      {"name": "ICT Order Block + Liq Sweep",  "min_hist": 20, "modes": ["SWING_SHORT","MEAN_REVERSION"]},
    "CVD_ABSORPTION":       {"name": "CVD Absorption Reversal",      "min_hist": 15, "modes": ["SCALP_SHORT","MEAN_REVERSION"]},
    "TRIPLE_SCREEN":        {"name": "Elder Triple Screen System",   "min_hist": 30, "modes": ["SWING_SHORT","MOMENTUM_SHORT"]},
    "CHANDE_MOMENTUM":      {"name": "Chande Momentum Oscillator",   "min_hist": 20, "modes": ["MOMENTUM_SHORT","SCALP_SHORT"]},
    "WADDAH_ATTAR":         {"name": "Waddah Attar Explosion",       "min_hist": 20, "modes": ["BREAKOUT_SHORT","MOMENTUM_SHORT"]},
    "HFT_STAT_ARB":         {"name": "HFT Statistical Arbitrage",    "min_hist": 10, "modes": ["SCALP_SHORT","GRID"]},
}

# ─────────────────────────────────────────────
# 9 TRADING MODES
# ─────────────────────────────────────────────
TRADING_MODES = {
    "SCALP_SHORT":    {"tp_mult": 0.4, "sl_mult": 0.2, "timeout": 8,  "direction": "SHORT"},
    "SCALP_LONG":     {"tp_mult": 0.4, "sl_mult": 0.2, "timeout": 8,  "direction": "LONG"},
    "SWING_SHORT":    {"tp_mult": 1.5, "sl_mult": 0.8, "timeout": 30, "direction": "SHORT"},
    "SWING_LONG":     {"tp_mult": 1.5, "sl_mult": 0.8, "timeout": 30, "direction": "LONG"},
    "BREAKOUT_SHORT": {"tp_mult": 1.0, "sl_mult": 0.5, "timeout": 15, "direction": "SHORT"},
    "BREAKOUT_LONG":  {"tp_mult": 1.0, "sl_mult": 0.5, "timeout": 15, "direction": "LONG"},
    "MOMENTUM_SHORT": {"tp_mult": 0.8, "sl_mult": 0.4, "timeout": 12, "direction": "SHORT"},
    "MOMENTUM_LONG":  {"tp_mult": 0.8, "sl_mult": 0.4, "timeout": 12, "direction": "LONG"},
    "MEAN_REVERSION": {"tp_mult": 0.6, "sl_mult": 0.3, "timeout": 20, "direction": "BOTH"},
    "GRID":           {"tp_mult": 0.3, "sl_mult": 0.15,"timeout": 10, "direction": "BOTH"},
}

# ─────────────────────────────────────────────
# 5 RISK PERSONALITY MODES
# ─────────────────────────────────────────────
RISK_MODES = {
    "SAFE":            {"emoji":"🛡️", "kelly":0.125, "tp_mult":0.6,  "sl_mult":0.5,  "min_conf":4, "max_open":2},
    "BALANCED":        {"emoji":"⚖️", "kelly":0.25,  "tp_mult":1.0,  "sl_mult":1.0,  "min_conf":3, "max_open":3},
    "AGGRESSIVE":      {"emoji":"⚔️", "kelly":0.375, "tp_mult":1.8,  "sl_mult":1.4,  "min_conf":2, "max_open":4},
    "ULTRA_AGGRESSIVE":{"emoji":"💀", "kelly":0.50,  "tp_mult":3.0,  "sl_mult":2.0,  "min_conf":2, "max_open":5},
    "CHAOS":           {"emoji":"🌪️", "kelly":1.0,   "tp_mult":None, "sl_mult":None, "min_conf":1, "max_open":5},
}
RISK_MODE_ORDER = ["SAFE","BALANCED","AGGRESSIVE","ULTRA_AGGRESSIVE","CHAOS"]

# ─────────────────────────────────────────────
# 20 AGENTS (19 specialists + TRADING GURU)
# ─────────────────────────────────────────────
AGENT_CONFIGS = [
    # Original 8
    {"name":"AGENT ALPHA",   "strategy":"EMA_CROSSOVER",         "risk":"BALANCED"},
    {"name":"AGENT BETA",    "strategy":"VWAP_MACD",             "risk":"AGGRESSIVE"},
    {"name":"AGENT GAMMA",   "strategy":"KELTNER_RSI",           "risk":"SAFE"},
    {"name":"AGENT DELTA",   "strategy":"BB_SQUEEZE",            "risk":"ULTRA_AGGRESSIVE"},
    {"name":"AGENT EPSILON", "strategy":"SUPERTREND_MACD",       "risk":"BALANCED"},
    {"name":"AGENT ZETA",    "strategy":"ORDER_FLOW",            "risk":"AGGRESSIVE"},
    # AGENT ETA reset → adopt PSI's Squeeze Momentum (top 5 performer)
    {"name":"AGENT ETA",     "strategy":"SQUEEZE_MOMENTUM",      "risk":"AGGRESSIVE"},
    {"name":"AGENT THETA",   "strategy":"ALMA_STOCH",            "risk":"SAFE"},
    # New 12 strategy agents
    {"name":"AGENT IOTA",    "strategy":"RANGE_TRADING",         "risk":"BALANCED"},
    {"name":"AGENT KAPPA",   "strategy":"PRICE_ACTION",          "risk":"AGGRESSIVE"},
    {"name":"AGENT LAMBDA",  "strategy":"PULLBACK_MOMENTUM",     "risk":"BALANCED"},
    {"name":"AGENT MU",      "strategy":"BREAKOUT_VOLUME",       "risk":"ULTRA_AGGRESSIVE"},
    # AGENT NU reset → adopt DALETH's Chande Momentum (top performer)
    {"name":"AGENT NU",      "strategy":"CHANDE_MOMENTUM",       "risk":"AGGRESSIVE"},
    {"name":"AGENT XI",      "strategy":"ICHIMOKU_CLOUD",        "risk":"BALANCED"},
    # AGENT OMICRON reset → adopt OMEGA's ICT Fair Value Gap (top 2 performer)
    {"name":"AGENT OMICRON", "strategy":"FAIR_VALUE_GAP",         "risk":"BALANCED"},
    {"name":"AGENT PI",      "strategy":"HEIKIN_ASHI_TREND",     "risk":"ULTRA_AGGRESSIVE"},
    {"name":"AGENT RHO",     "strategy":"WILLIAMS_R_REVERSAL",   "risk":"SAFE"},
    {"name":"AGENT SIGMA",   "strategy":"ADX_TREND_STRENGTH",    "risk":"BALANCED"},
    {"name":"AGENT TAU",     "strategy":"PARABOLIC_SAR",         "risk":"AGGRESSIVE"},
    {"name":"AGENT UPSILON", "strategy":"TRIPLE_EMA",            "risk":"CHAOS"},
    # New 10 deep research agents
    {"name":"AGENT PHI",     "strategy":"DONCHIAN_BREAKOUT",     "risk":"AGGRESSIVE"},
    # AGENT CHI reset → adopt GAMMA's Keltner+RSI (top 4 performer)
    {"name":"AGENT CHI",     "strategy":"KELTNER_RSI",           "risk":"SAFE"},
    {"name":"AGENT PSI",     "strategy":"SQUEEZE_MOMENTUM",      "risk":"ULTRA_AGGRESSIVE"},
    {"name":"AGENT OMEGA",   "strategy":"FAIR_VALUE_GAP",        "risk":"BALANCED"},
    {"name":"AGENT ALEPH",   "strategy":"ORDER_BLOCK_LIQ",       "risk":"AGGRESSIVE"},
    {"name":"AGENT BETH",    "strategy":"CVD_ABSORPTION",        "risk":"SAFE"},
    # AGENT GIMEL reset → adopt ZETA's Order Flow Imbalance (top 3 performer)
    {"name":"AGENT GIMEL",   "strategy":"ORDER_FLOW",            "risk":"AGGRESSIVE"},
    {"name":"AGENT DALETH",  "strategy":"CHANDE_MOMENTUM",       "risk":"AGGRESSIVE"},
    {"name":"AGENT HE",      "strategy":"WADDAH_ATTAR",          "risk":"ULTRA_AGGRESSIVE"},
    {"name":"AGENT VAV",     "strategy":"HFT_STAT_ARB",          "risk":"CHAOS"},
    # Master agent
    # TRADING GURU → boots from DALETH's strategy (top performer); will keep
    # self-learning from the live leaderboard at runtime.
    {"name":"TRADING GURU",  "strategy":"CHANDE_MOMENTUM",       "risk":"AGGRESSIVE"},
]

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
os.makedirs(BASE_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("engine")

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, agent_name TEXT, strategy TEXT,
        trading_mode TEXT, risk_mode TEXT, direction TEXT,
        asset TEXT, entry_price REAL, exit_price REAL,
        stop_loss REAL, take_profit REAL, position_size REAL,
        capital_before REAL, capital_after REAL,
        pnl_usd REAL, pnl_pct REAL, outcome TEXT, close_reason TEXT,
        open_tick INTEGER, close_tick INTEGER,
        open_time TEXT, close_time TEXT, confirms INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, start_time TEXT, end_time TEXT,
        total_trades INTEGER, total_pnl REAL, version TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS learning_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tick INTEGER, timestamp TEXT,
        adopted_strategy TEXT, adopted_from TEXT,
        win_rate REAL, reason TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS agent_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tick INTEGER, timestamp TEXT, agent_name TEXT,
        strategy TEXT, risk_mode TEXT, capital REAL,
        cold_wallet REAL, total_trades INTEGER,
        wins INTEGER, losses INTEGER, win_rate REAL
    )""")
    # Migrate: add risk_mode column if missing
    try:
        c.execute("ALTER TABLE trades ADD COLUMN risk_mode TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()

def save_trade(trade_dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO trades
        (session_id,agent_name,strategy,trading_mode,risk_mode,direction,asset,
         entry_price,exit_price,stop_loss,take_profit,position_size,
         capital_before,capital_after,pnl_usd,pnl_pct,outcome,close_reason,
         open_tick,close_tick,open_time,close_time,confirms)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (trade_dict.get("session_id",""),trade_dict.get("agent_name",""),
         trade_dict.get("strategy",""),trade_dict.get("trading_mode",""),
         trade_dict.get("risk_mode",""),trade_dict.get("direction",""),
         trade_dict.get("asset",""),trade_dict.get("entry_price",0),
         trade_dict.get("exit_price",0),trade_dict.get("stop_loss",0),
         trade_dict.get("take_profit",0),trade_dict.get("position_size",0),
         trade_dict.get("capital_before",0),trade_dict.get("capital_after",0),
         trade_dict.get("pnl_usd",0),trade_dict.get("pnl_pct",0),
         trade_dict.get("outcome",""),trade_dict.get("close_reason",""),
         trade_dict.get("open_tick",0),trade_dict.get("close_tick",0),
         trade_dict.get("open_time",""),trade_dict.get("close_time",""),
         trade_dict.get("confirms",0)))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# INDICATOR CALCULATIONS
# ─────────────────────────────────────────────
def ema(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    k = 2 / (period + 1)
    result = prices[0]
    for p in prices[1:]:
        result = p * k + result * (1 - k)
    return result

def sma(prices, period):
    if len(prices) < period:
        return sum(prices) / len(prices)
    return sum(prices[-period:]) / period

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow:
        return 0, 0, 0
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast - ema_slow
    # simplified signal
    signal_line = macd_line * 0.9
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def bollinger_bands(prices, period=20, std_mult=2.0):
    if len(prices) < period:
        p = prices[-1]
        return p, p, p
    recent = prices[-period:]
    mid = sum(recent) / period
    variance = sum((x - mid)**2 for x in recent) / period
    std = math.sqrt(variance)
    return mid + std_mult * std, mid, mid - std_mult * std

def stochastic(prices, period=14):
    if len(prices) < period:
        return 50.0
    recent = prices[-period:]
    low_min = min(recent)
    high_max = max(recent)
    if high_max == low_min:
        return 50.0
    return 100 * (prices[-1] - low_min) / (high_max - low_min)

def atr_pct(prices, period=14):
    if len(prices) < 2:
        return TOKEN_ATR.get("BTC/USDT", 0.005)
    ranges = [abs(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
    recent = ranges[-period:] if len(ranges) >= period else ranges
    return sum(recent) / len(recent) if recent else 0.005

def williams_r(prices, period=14):
    if len(prices) < period:
        return -50.0
    recent = prices[-period:]
    high_max = max(recent)
    low_min = min(recent)
    if high_max == low_min:
        return -50.0
    return -100 * (high_max - prices[-1]) / (high_max - low_min)

def adx_simple(prices, period=14):
    """Simplified ADX approximation"""
    if len(prices) < period + 1:
        return 25.0
    moves = [abs(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices))]
    recent = moves[-period:]
    return min(sum(recent) / len(recent) * 10, 100)

def heikin_ashi(prices):
    """Returns HA close and direction"""
    if len(prices) < 3:
        return prices[-1], "NEUTRAL"
    ha_close = sum(prices[-3:]) / 3
    ha_open = (prices[-3] + prices[-2]) / 2
    direction = "BULLISH" if ha_close > ha_open else "BEARISH"
    return ha_close, direction

def parabolic_sar(prices, af_start=0.02, af_max=0.2):
    """Simplified Parabolic SAR — returns direction"""
    if len(prices) < 5:
        return "NEUTRAL"
    trend = "UP" if prices[-1] > prices[-5] else "DOWN"
    return trend

def ichimoku_signal(prices):
    """Simplified Ichimoku — returns signal based on Tenkan/Kijun cross"""
    if len(prices) < 26:
        return "NEUTRAL"
    tenkan = (max(prices[-9:]) + min(prices[-9:])) / 2
    kijun = (max(prices[-26:]) + min(prices[-26:])) / 2
    if prices[-1] > tenkan > kijun:
        return "BULLISH"
    elif prices[-1] < tenkan < kijun:
        return "BEARISH"
    return "NEUTRAL"

def fibonacci_levels(prices, lookback=30):
    """Returns fib levels from recent swing"""
    if len(prices) < lookback:
        lookback = len(prices)
    recent = prices[-lookback:]
    high = max(recent)
    low = min(recent)
    diff = high - low
    return {
        "0.236": high - 0.236 * diff,
        "0.382": high - 0.382 * diff,
        "0.500": high - 0.500 * diff,
        "0.618": high - 0.618 * diff,
        "0.786": high - 0.786 * diff,
    }

# ─────────────────────────────────────────────
# STRATEGY SIGNAL GENERATORS
# ─────────────────────────────────────────────
def get_signal(strategy_key: str, prices: list, token: str) -> Tuple[str, int]:
    """Returns (direction, confirms) — direction: LONG/SHORT/NONE"""
    if len(prices) < 5:
        return "NONE", 0

    p = prices
    curr = p[-1]
    confirms = 0
    direction = "NONE"

    if strategy_key == "EMA_CROSSOVER":
        if len(p) >= 21:
            e9 = ema(p, 9); e21 = ema(p, 21)
            prev_e9 = ema(p[:-1], 9); prev_e21 = ema(p[:-1], 21)
            r = rsi(p)
            vol_ok = len(p) >= 5 and p[-1] != p[-5]
            if e9 < e21 and prev_e9 >= prev_e21:
                direction = "SHORT"; confirms += 2
            elif e9 > e21 and prev_e9 <= prev_e21:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 55: confirms += 1
            if direction == "LONG" and r < 45: confirms += 1
            if vol_ok: confirms += 1

    elif strategy_key == "VWAP_MACD":
        if len(p) >= 20:
            vwap = sma(p, 20)
            ml, sl_line, hist = macd(p)
            r = rsi(p)
            if curr < vwap and hist < 0:
                direction = "SHORT"; confirms += 2
            elif curr > vwap and hist > 0:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 50: confirms += 1
            if direction == "LONG" and r < 50: confirms += 1
            if abs(curr - vwap) / vwap > 0.003: confirms += 1

    elif strategy_key == "KELTNER_RSI":
        if len(p) >= 20:
            mid = sma(p, 20)
            atr = atr_pct(p) * curr
            upper = mid + 1.5 * atr; lower = mid - 1.5 * atr
            r = rsi(p)
            if curr > upper and r > 65:
                direction = "SHORT"; confirms += 2
            elif curr < lower and r < 35:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 70: confirms += 1
            if direction == "LONG" and r < 30: confirms += 1
            if abs(curr - mid) / mid > 0.005: confirms += 1

    elif strategy_key == "BB_SQUEEZE":
        if len(p) >= 20:
            upper, mid, lower = bollinger_bands(p)
            bw = (upper - lower) / mid
            ml, _, hist = macd(p)
            if bw < 0.03 and curr > upper:
                direction = "SHORT"; confirms += 2
            elif bw < 0.03 and curr < lower:
                direction = "LONG"; confirms += 2
            if bw < 0.02: confirms += 1
            if direction == "SHORT" and hist < 0: confirms += 1
            if direction == "LONG" and hist > 0: confirms += 1
            if abs(curr - mid) / mid > 0.01: confirms += 1

    elif strategy_key == "SUPERTREND_MACD":
        if len(p) >= 20:
            atr = atr_pct(p) * curr * 3
            mid = sma(p, 10)
            ml, _, hist = macd(p)
            r = rsi(p)
            if curr < mid - atr and hist < 0:
                direction = "SHORT"; confirms += 2
            elif curr > mid + atr and hist > 0:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 50: confirms += 1
            if direction == "LONG" and r < 50: confirms += 1
            if abs(hist) > 0.001 * curr: confirms += 1

    elif strategy_key == "ORDER_FLOW":
        if len(p) >= 5:
            recent_moves = [p[i] - p[i-1] for i in range(1, len(p))]
            sell_pressure = sum(1 for m in recent_moves[-5:] if m < 0)
            buy_pressure  = sum(1 for m in recent_moves[-5:] if m > 0)
            r = rsi(p)
            if sell_pressure >= 4:
                direction = "SHORT"; confirms += sell_pressure
            elif buy_pressure >= 4:
                direction = "LONG"; confirms += buy_pressure
            if direction == "SHORT" and r > 55: confirms += 1
            if direction == "LONG" and r < 45: confirms += 1

    elif strategy_key == "PIVOT_BREAKDOWN":
        if len(p) >= 15:
            pivot = sma(p, 15)
            r1 = pivot + (max(p[-15:]) - pivot) * 0.5
            s1 = pivot - (pivot - min(p[-15:])) * 0.5
            r = rsi(p)
            if curr < s1:
                direction = "SHORT"; confirms += 2
            elif curr > r1:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 50: confirms += 1
            if direction == "LONG" and r < 50: confirms += 1
            if abs(curr - pivot) / pivot > 0.005: confirms += 1

    elif strategy_key == "ALMA_STOCH":
        if len(p) >= 20:
            # ALMA approximation using weighted EMA
            weights = [math.exp(-((i - len(p[-20:]))**2) / (2 * (len(p[-20:]) * 0.85)**2))
                       for i in range(len(p[-20:]))]
            alma_val = sum(w * v for w, v in zip(weights, p[-20:])) / sum(weights)
            stoch = stochastic(p)
            if curr > alma_val and stoch > 80:
                direction = "SHORT"; confirms += 2
            elif curr < alma_val and stoch < 20:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and stoch > 85: confirms += 1
            if direction == "LONG" and stoch < 15: confirms += 1
            if abs(curr - alma_val) / alma_val > 0.003: confirms += 1

    elif strategy_key == "RANGE_TRADING":
        if len(p) >= 20:
            high = max(p[-20:]); low = min(p[-20:])
            rng = high - low
            r = rsi(p)
            if rng / curr < 0.03:  # ranging market
                if curr >= high - rng * 0.1:
                    direction = "SHORT"; confirms += 2
                elif curr <= low + rng * 0.1:
                    direction = "LONG"; confirms += 2
                if direction == "SHORT" and r > 65: confirms += 1
                if direction == "LONG" and r < 35: confirms += 1
                if rng / curr < 0.02: confirms += 1

    elif strategy_key == "PRICE_ACTION":
        if len(p) >= 5:
            # Bullish/bearish engulfing approximation
            body1 = p[-2] - p[-3]
            body2 = p[-1] - p[-2]
            r = rsi(p)
            if body1 > 0 and body2 < body1 * -1.5:  # bearish engulf
                direction = "SHORT"; confirms += 2
            elif body1 < 0 and body2 > abs(body1) * 1.5:  # bullish engulf
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 55: confirms += 1
            if direction == "LONG" and r < 45: confirms += 1
            if abs(body2) > abs(body1) * 2: confirms += 1

    elif strategy_key == "PULLBACK_MOMENTUM":
        if len(p) >= 50:
            e50 = ema(p, 50)
            r = rsi(p)
            ml, _, hist = macd(p)
            # Uptrend pullback
            if curr > e50 and r < 50 and hist > 0:
                direction = "LONG"; confirms += 2
            # Downtrend pullback
            elif curr < e50 and r > 50 and hist < 0:
                direction = "SHORT"; confirms += 2
            if direction == "LONG" and 40 <= r <= 50: confirms += 1
            if direction == "SHORT" and 50 <= r <= 60: confirms += 1
            if abs(curr - e50) / e50 < 0.01: confirms += 1

    elif strategy_key == "BREAKOUT_VOLUME":
        if len(p) >= 20:
            high20 = max(p[-20:]); low20 = min(p[-20:])
            recent_moves = [abs(p[i] - p[i-1]) for i in range(1, len(p))]
            avg_move = sum(recent_moves[-20:]) / 20 if len(recent_moves) >= 20 else recent_moves[-1]
            curr_move = abs(p[-1] - p[-2]) if len(p) >= 2 else 0
            volume_surge = curr_move > avg_move * 1.5
            if curr > high20 and volume_surge:
                direction = "LONG"; confirms += 3
            elif curr < low20 and volume_surge:
                direction = "SHORT"; confirms += 3
            if volume_surge: confirms += 1

    elif strategy_key == "RSI_DIVERGENCE":
        if len(p) >= 20:
            r = rsi(p)
            r_prev = rsi(p[:-3])
            # Bearish divergence: price up, RSI down
            if p[-1] > p[-4] and r < r_prev and r > 60:
                direction = "SHORT"; confirms += 3
            # Bullish divergence: price down, RSI up
            elif p[-1] < p[-4] and r > r_prev and r < 40:
                direction = "LONG"; confirms += 3
            if direction == "SHORT" and r > 65: confirms += 1
            if direction == "LONG" and r < 35: confirms += 1

    elif strategy_key == "ICHIMOKU_CLOUD":
        if len(p) >= 26:
            signal_ichi = ichimoku_signal(p)
            r = rsi(p)
            if signal_ichi == "BEARISH":
                direction = "SHORT"; confirms += 2
            elif signal_ichi == "BULLISH":
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 50: confirms += 1
            if direction == "LONG" and r < 50: confirms += 1
            tenkan = (max(p[-9:]) + min(p[-9:])) / 2
            kijun = (max(p[-26:]) + min(p[-26:])) / 2
            if abs(tenkan - kijun) / kijun > 0.005: confirms += 1

    elif strategy_key == "FIBONACCI_RETRACEMENT":
        if len(p) >= 30:
            fibs = fibonacci_levels(p)
            r = rsi(p)
            # Price near 0.618 retracement in downtrend
            near_618 = abs(curr - fibs["0.618"]) / curr < 0.005
            near_382 = abs(curr - fibs["0.382"]) / curr < 0.005
            if near_618 and r > 55:
                direction = "SHORT"; confirms += 2
            elif near_382 and r < 45:
                direction = "LONG"; confirms += 2
            if near_618 or near_382: confirms += 1
            if direction == "SHORT" and r > 60: confirms += 1
            if direction == "LONG" and r < 40: confirms += 1

    elif strategy_key == "HEIKIN_ASHI_TREND":
        if len(p) >= 5:
            _, ha_dir = heikin_ashi(p)
            r = rsi(p)
            ml, _, hist = macd(p)
            if ha_dir == "BEARISH" and hist < 0:
                direction = "SHORT"; confirms += 2
            elif ha_dir == "BULLISH" and hist > 0:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 50: confirms += 1
            if direction == "LONG" and r < 50: confirms += 1
            if abs(hist) > 0: confirms += 1

    elif strategy_key == "WILLIAMS_R_REVERSAL":
        if len(p) >= 14:
            wr = williams_r(p)
            r = rsi(p)
            if wr > -20:  # overbought
                direction = "SHORT"; confirms += 2
            elif wr < -80:  # oversold
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 65: confirms += 1
            if direction == "LONG" and r < 35: confirms += 1
            if direction == "SHORT" and wr > -10: confirms += 1
            if direction == "LONG" and wr < -90: confirms += 1

    elif strategy_key == "ADX_TREND_STRENGTH":
        if len(p) >= 20:
            adx = adx_simple(p)
            r = rsi(p)
            ml, _, hist = macd(p)
            if adx > 25 and hist < 0 and r > 50:
                direction = "SHORT"; confirms += 2
            elif adx > 25 and hist > 0 and r < 50:
                direction = "LONG"; confirms += 2
            if adx > 35: confirms += 1
            if direction == "SHORT" and r > 60: confirms += 1
            if direction == "LONG" and r < 40: confirms += 1

    elif strategy_key == "PARABOLIC_SAR":
        if len(p) >= 5:
            sar_dir = parabolic_sar(p)
            r = rsi(p)
            ml, _, hist = macd(p)
            if sar_dir == "DOWN":
                direction = "SHORT"; confirms += 2
            elif sar_dir == "UP":
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 50: confirms += 1
            if direction == "LONG" and r < 50: confirms += 1
            if abs(hist) > 0: confirms += 1

    elif strategy_key == "TRIPLE_EMA":
        if len(p) >= 34:
            e5 = ema(p, 5); e13 = ema(p, 13); e34 = ema(p, 34)
            r = rsi(p)
            if e5 < e13 < e34:  # bearish alignment
                direction = "SHORT"; confirms += 3
            elif e5 > e13 > e34:  # bullish alignment
                direction = "LONG"; confirms += 3
            if direction == "SHORT" and r > 50: confirms += 1
            if direction == "LONG" and r < 50: confirms += 1
            if abs(e5 - e34) / e34 > 0.005: confirms += 1

    # ── NEW 10 DEEP RESEARCH STRATEGIES ──────────────────────────────────────
    elif strategy_key == "DONCHIAN_BREAKOUT":
        # Donchian Channel: break below lowest low of N periods = SHORT
        if len(p) >= 20:
            period = 20
            highest = max(p[-period:])
            lowest  = min(p[-period:-1])  # exclude current
            prev_lowest = min(p[-period-1:-1]) if len(p) > period else lowest
            r = rsi(p)
            ml, _, hist = macd(p)
            # SHORT: price breaks below Donchian lower band
            if curr < lowest and curr < p[-2]:
                direction = "SHORT"; confirms += 3
            # LONG: price breaks above Donchian upper band
            elif curr > highest and curr > p[-2]:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r < 50: confirms += 1
            if direction == "SHORT" and hist < 0: confirms += 1
            if abs(curr - lowest) / lowest < 0.003: confirms += 1  # tight to band

    elif strategy_key == "LAGUERRE_RSI":
        # Laguerre RSI: smooth oscillator with gamma=0.5
        # L0 = (1-g)*price + g*L0_prev; L1 = -g*L0 + L0_prev + g*L1_prev; etc.
        if len(p) >= 15:
            g = 0.5
            L0, L1, L2, L3 = p[-1], p[-2], p[-3], p[-4]
            for i in range(min(len(p)-1, 14), 0, -1):
                nL0 = (1-g)*p[-i] + g*L0
                nL1 = -g*nL0 + L0 + g*L1
                nL2 = -g*nL1 + L1 + g*L2
                nL3 = -g*nL2 + L2 + g*L3
                L0, L1, L2, L3 = nL0, nL1, nL2, nL3
            cu = max(L0-L1, 0) + max(L1-L2, 0) + max(L2-L3, 0)
            cd = max(L1-L0, 0) + max(L2-L1, 0) + max(L3-L2, 0)
            lrsi = cu / (cu + cd + 1e-9)
            r = rsi(p)
            e20 = ema(p, 20)
            # SHORT: Laguerre RSI crosses below 0.8 (overbought)
            if lrsi < 0.8 and lrsi > 0.5:
                direction = "SHORT"; confirms += 2
            # LONG: Laguerre RSI crosses above 0.2 (oversold)
            elif lrsi > 0.2 and lrsi < 0.5:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and curr > e20: confirms += 1
            if direction == "LONG"  and curr < e20: confirms += 1
            if direction == "SHORT" and r > 60: confirms += 1
            if direction == "LONG"  and r < 40: confirms += 1

    elif strategy_key == "SQUEEZE_MOMENTUM":
        # LazyBear Squeeze Momentum: BB inside KC = squeeze, momentum direction
        if len(p) >= 20:
            bb_upper, bb_mid, bb_lower = bollinger_bands(p, 20, 2.0)
            # Inline Keltner Channel calculation
            kc_mid = sma(p, 20)
            kc_atr = atr_pct(p) * curr
            kc_upper = kc_mid + 1.5 * kc_atr
            kc_lower = kc_mid - 1.5 * kc_atr
            squeeze = (bb_upper < kc_upper) and (bb_lower > kc_lower)
            # Momentum = price - midpoint of (highest high + lowest low + SMA)
            highest20 = max(p[-20:]); lowest20 = min(p[-20:])
            s20 = sma(p, 20)
            momentum = curr - (highest20 + lowest20) / 2 - s20
            r = rsi(p)
            ml, _, hist = macd(p)
            if not squeeze:  # squeeze released = breakout
                if momentum < 0:
                    direction = "SHORT"; confirms += 3
                elif momentum > 0:
                    direction = "LONG"; confirms += 2
            else:  # squeeze active = anticipate breakout
                if momentum < 0 and hist < 0:
                    direction = "SHORT"; confirms += 2
            if direction == "SHORT" and r > 50: confirms += 1
            if direction == "SHORT" and hist < 0: confirms += 1

    elif strategy_key == "FAIR_VALUE_GAP":
        # ICT Fair Value Gap: 3-candle imbalance pattern
        # Bearish FVG: candle[i-2].high < candle[i].low (gap between them)
        if len(p) >= 10:
            # Simulate candle bodies from price sequence
            # Use price[i] as close, price[i-1] as open approximation
            c1_high = max(p[-5], p[-4])  # candle 1 high
            c3_low  = min(p[-2], p[-1])  # candle 3 low
            c2_body = abs(p[-3] - p[-4]) # candle 2 body size
            r = rsi(p)
            e20 = ema(p, 20)
            # Bearish FVG: gap between c1 high and c3 low, price in premium zone
            if c1_high < c3_low and curr > e20:
                direction = "SHORT"; confirms += 3  # price in FVG zone, expect fill
            # Bullish FVG: c1 low > c3 high, price in discount zone
            elif c1_high > c3_low and curr < e20:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 55: confirms += 1
            if direction == "SHORT" and c2_body > atr_pct(p) * curr: confirms += 1
            if curr > e20 * 1.005: confirms += 1  # premium zone

    elif strategy_key == "ORDER_BLOCK_LIQ":
        # ICT Order Block + Liquidity Sweep
        # Order block = last bearish candle before bullish impulse (resistance)
        # Liquidity sweep = price spikes above recent high then reverses
        if len(p) >= 20:
            recent_high = max(p[-20:-1])
            recent_low  = min(p[-20:-1])
            e20 = ema(p, 20)
            r = rsi(p)
            ml, _, hist = macd(p)
            # Liquidity sweep SHORT: price spikes above recent high then reverses
            if p[-2] > recent_high and curr < p[-2] * 0.998:
                direction = "SHORT"; confirms += 4  # strong sweep signal
            # Order block SHORT: price returns to bearish OB zone (near recent high)
            elif curr > recent_high * 0.995 and curr < recent_high * 1.005:
                direction = "SHORT"; confirms += 2
            if direction == "SHORT" and r > 60: confirms += 1
            if direction == "SHORT" and hist < 0: confirms += 1

    elif strategy_key == "CVD_ABSORPTION":
        # Cumulative Volume Delta: net buy vs sell pressure
        # Approximate CVD from price momentum (no order book data)
        if len(p) >= 15:
            # CVD proxy: sum of signed price changes
            deltas = [p[i] - p[i-1] for i in range(1, len(p))]
            cvd = sum(deltas[-10:])  # 10-period CVD
            cvd_prev = sum(deltas[-15:-5]) if len(deltas) >= 15 else cvd
            r = rsi(p)
            e20 = ema(p, 20)
            # Absorption SHORT: price rising but CVD falling (selling pressure)
            if curr > e20 and cvd < cvd_prev and cvd < 0:
                direction = "SHORT"; confirms += 3
            # Absorption LONG: price falling but CVD rising (buying pressure)
            elif curr < e20 and cvd > cvd_prev and cvd > 0:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 60: confirms += 1
            if direction == "SHORT" and curr > e20 * 1.003: confirms += 1

    elif strategy_key == "TRIPLE_SCREEN":
        # Elder Triple Screen: weekly trend + daily oscillator + hourly entry
        # Simulate 3 timeframes from price history
        if len(p) >= 30:
            # Screen 1 (weekly): long-term EMA trend
            e34 = ema(p, 34)
            trend_up = curr > e34
            # Screen 2 (daily): oscillator in opposite direction
            r = rsi(p)
            ml, sl_line, hist = macd(p)
            # Screen 3 (hourly): entry trigger
            e5 = ema(p, 5)
            e13 = ema(p, 13)
            # SHORT setup: downtrend + RSI overbought + EMA death cross
            if not trend_up and r > 60 and e5 < e13:
                direction = "SHORT"; confirms += 4
            elif not trend_up and hist < 0:
                direction = "SHORT"; confirms += 2
            # LONG setup: uptrend + RSI oversold + EMA golden cross
            elif trend_up and r < 40 and e5 > e13:
                direction = "LONG"; confirms += 3
            if direction == "SHORT" and r > 65: confirms += 1

    elif strategy_key == "CHANDE_MOMENTUM":
        # Chande Momentum Oscillator (CMO): measures momentum -100 to +100
        if len(p) >= 20:
            period = 14
            ups   = sum(max(p[i]-p[i-1], 0) for i in range(-period, 0))
            downs = sum(max(p[i-1]-p[i], 0) for i in range(-period, 0))
            cmo = 100 * (ups - downs) / (ups + downs + 1e-9)
            r = rsi(p)
            e20 = ema(p, 20)
            ml, _, hist = macd(p)
            # SHORT: CMO > 50 (overbought momentum)
            if cmo > 50:
                direction = "SHORT"; confirms += 3
            elif cmo > 30:
                direction = "SHORT"; confirms += 1
            # LONG: CMO < -50 (oversold momentum)
            elif cmo < -50:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 60: confirms += 1
            if direction == "SHORT" and hist < 0: confirms += 1
            if direction == "SHORT" and curr > e20: confirms += 1

    elif strategy_key == "WADDAH_ATTAR":
        # Waddah Attar Explosion: MACD histogram * BB width = explosion bars
        if len(p) >= 20:
            ml, sl_line, hist = macd(p)
            bb_upper, bb_mid_wa, bb_lower = bollinger_bands(p, 20, 2.0)
            bb_width = (bb_upper - bb_lower) / sma(p, 20)
            # Explosion value = MACD histogram * BB width * 100
            explosion = abs(hist) * bb_width * 100
            r = rsi(p)
            e20 = ema(p, 20)
            # Bearish explosion: negative MACD + wide BB
            if hist < 0 and explosion > 0.5:
                direction = "SHORT"; confirms += 3
            elif hist < 0 and explosion > 0.2:
                direction = "SHORT"; confirms += 1
            # Bullish explosion: positive MACD + wide BB
            elif hist > 0 and explosion > 0.5:
                direction = "LONG"; confirms += 2
            if direction == "SHORT" and r > 50: confirms += 1
            if direction == "SHORT" and bb_width > 0.02: confirms += 1  # volatile
            if direction == "SHORT" and curr < e20: confirms += 1

    elif strategy_key == "HFT_STAT_ARB":
        # HFT Statistical Arbitrage: mean reversion on short-term z-score
        # Z-score = (price - mean) / std; trade when |z| > threshold
        if len(p) >= 10:
            window = 10
            mean = sma(p, window)
            variance = sum((x - mean)**2 for x in p[-window:]) / window
            std = variance ** 0.5 + 1e-9
            z_score = (curr - mean) / std
            r = rsi(p)
            # SHORT: price significantly above mean (z > 1.5)
            if z_score > 1.5:
                direction = "SHORT"; confirms += 3
            elif z_score > 1.0:
                direction = "SHORT"; confirms += 2
            # LONG: price significantly below mean (z < -1.5)
            elif z_score < -1.5:
                direction = "LONG"; confirms += 2
            elif z_score < -1.0:
                direction = "LONG"; confirms += 1
            if direction == "SHORT" and r > 65: confirms += 1
            if direction == "LONG"  and r < 35: confirms += 1
            if abs(z_score) > 2.0: confirms += 1  # extreme deviation

    return direction, confirms

# ─────────────────────────────────────────────
# POSITION SIZING — GODS LEVEL
# ─────────────────────────────────────────────
def gods_level_position(capital, token, prices, risk_mode_key, confirms, max_confirms=5):
    rm = RISK_MODES[risk_mode_key]
    kelly = rm["kelly"]
    risk_dollar = capital * RISK_PER_TRADE
    base_atr = TOKEN_ATR.get(token, 0.008)
    dynamic_atr = atr_pct(prices) if len(prices) >= 5 else base_atr
    atr = max(dynamic_atr, base_atr * 0.5)
    conf_factor = 1.0 - (confirms / max_confirms) * 0.3
    if risk_mode_key == "CHAOS":
        sl_pct = random.uniform(0.002, 0.015)
        # CHAOS: TP target is now anchored to TP_SL_RATIO (no longer can be sub-1x SL)
        tp_pct = sl_pct * TP_SL_RATIO * random.uniform(0.9, 1.4)
    else:
        sl_pct = atr * conf_factor * rm["sl_mult"]
        # Enforce a robust TP:SL ratio so winners outsize losers (was effectively
        # tp_mult * 2x sl, but tp_mult on SAFE/BALANCED was ≤ 1.0 → ratio collapsed).
        tp_pct = sl_pct * TP_SL_RATIO * max(rm["tp_mult"], 1.0)
    sl_pct = max(sl_pct, 0.001)
    tp_pct = max(tp_pct, sl_pct * TP_SL_RATIO)  # never let TP fall below ratio floor
    base_pos = risk_dollar / sl_pct
    final_pos = base_pos * kelly
    return round(final_pos, 2), round(sl_pct, 6), round(tp_pct, 6)

# ─────────────────────────────────────────────
# AGENT CLASS
# ─────────────────────────────────────────────
class Agent:
    def __init__(self, name, strategy_key, risk_mode, session_id):
        self.name = name
        self.strategy_key = strategy_key
        self.risk_mode = risk_mode
        self.session_id = session_id
        self.capital = STARTING_CAPITAL
        self.cold_wallet = 0.0
        self.open_trades = []
        self.closed_trades = []
        self.wins = 0
        self.losses = 0
        self.halted = False
        self.halt_reason = ""
        self.last_risk_adapt = 0
        # ── Anti-Martingale System (DEFAULT sizing — all 31 agents) ─────────
        # WIN-TRIGGERED: WIN → streak +1 (max 3 = 8x), LOSS → reset streak to 0
        # MULTIPLIER: 2^streak  (0→1x, 1→2x, 2→4x, 3→8x)
        # BASE BET: 2% of capital (RISK_PER_TRADE), hard cap 8% per trade
        self.doubling_active = False      # True when win streak >= 1
        self.doubling_level = 0           # Win streak (0=1x, 1=2x, 2=4x, 3=8x)
        self.doubling_last_loss_tick = -1 # Last loss tick (kept for compat)
        self.doubling_wins = 0            # Wins accumulated during active streaks
        self.doubling_losses = 0          # Total streak resets (loss count)
        self.doubling_profit = 0.0        # Net PnL accumulated during streaks
        self.doubling_8x_cycles = 0         # Total completed 8x (streak=3) cycles
        self.doubling_8x_last_tick = -1     # Tick when last 8x cycle completed
        self.doubling_8x_last_profit = 0.0  # PnL of the last completed 8x cycle
        # ──────────────────────────────────────────────────────────────────

    @property
    def total_trades(self):
        return self.wins + self.losses

    @property
    def win_rate(self):
        if self.total_trades == 0:
            return 0.0
        return self.wins / self.total_trades

    def adapt_risk_mode(self, tick):
        if tick - self.last_risk_adapt < RISK_ADAPT_EVERY:
            return
        if self.total_trades < 10:
            return
        self.last_risk_adapt = tick
        wr = self.win_rate
        idx = RISK_MODE_ORDER.index(self.risk_mode)
        if wr > 0.60 and idx < len(RISK_MODE_ORDER) - 1:
            self.risk_mode = RISK_MODE_ORDER[idx + 1]
            log.info(f"[{self.name}] 📈 RISK UPGRADE → {self.risk_mode} (WR={wr:.1%})")
        elif wr < 0.40 and idx > 0:
            self.risk_mode = RISK_MODE_ORDER[idx - 1]
            log.info(f"[{self.name}] 📉 RISK DOWNGRADE → {self.risk_mode} (WR={wr:.1%})")

    def check_halt(self):
        # UNSTOPPABLE MODE: agents never halt — they keep trading 24/7
        # Only auto-recover if capital was previously halted
        if self.halted and self.capital >= STARTING_CAPITAL * 0.50:
            self.halted = False
            self.halt_reason = ""
            log.info(f"[{self.name}] 🔄 AUTO-RECOVERED — resuming trading")

    def try_open_trade(self, token, prices, tick):
        if self.halted:
            return
        rm = RISK_MODES[self.risk_mode]
        if len(self.open_trades) >= min(rm["max_open"], MAX_OPEN_PER_AGENT):
            return
        # Check if already trading this token
        if any(t["asset"] == token for t in self.open_trades):
            return
        # Skip tokens whose live price is missing/zero (offline feed)
        if not prices or prices[-1] is None or prices[-1] <= MIN_PRICE_FLOOR:
            return
        strat = STRATEGIES[self.strategy_key]
        if len(prices) < strat["min_hist"]:
            return
        direction, confirms = get_signal(self.strategy_key, prices, token)
        if direction == "NONE" or confirms < rm["min_conf"]:
            return
        # ── SHORT-ONLY enforcement (project rule, applies to ALL agents) ─────────
        if SHORT_ONLY and direction != "SHORT":
            return
        # Pick trading mode — prefer SHORT/BOTH modes only when SHORT_ONLY is on
        candidate_modes = strat["modes"]
        if SHORT_ONLY:
            short_modes = [m for m in candidate_modes
                           if TRADING_MODES[m]["direction"] in ("SHORT", "BOTH")]
            if not short_modes:
                # Strategy has no SHORT-capable mode — fall back to a global SHORT mode
                short_modes = ["SCALP_SHORT"]
            candidate_modes = short_modes
        mode_key = random.choice(candidate_modes)
        mode = TRADING_MODES[mode_key]
        # Respect direction constraint
        if mode["direction"] != "BOTH" and mode["direction"] != direction:
            return
        pos_size, sl_pct, tp_pct = gods_level_position(
            self.capital, token, prices, self.risk_mode, confirms)
        if pos_size < 1.0:
            return
        # ── Anti-Martingale: apply win-streak multiplier ──
        # streak=0 → 1x (base), streak=1 → 2x, streak=2 → 4x, streak=3 → 8x
        if self.doubling_level > 0:
            am_mult = min(2 ** self.doubling_level, 8)
            # Hard cap: position cannot exceed 8% of capital
            max_pos = self.capital * 0.08 / max(0.001, pos_size / self.capital)
            pos_size = round(min(pos_size * am_mult, max_pos), 2)
            log.info(f"[{self.name}] 🚀 ANTI-MARTINGALE streak={self.doubling_level} "
                     f"mult={am_mult}x pos=${pos_size:.0f} conf={confirms}")
        entry = prices[-1]
        if direction == "SHORT":
            sl = entry * (1 + sl_pct)
            tp = entry * (1 - tp_pct)
        else:
            sl = entry * (1 - sl_pct)
            tp = entry * (1 + tp_pct)
        trade = {
            "session_id": self.session_id,
            "agent_name": self.name,
            "strategy": STRATEGIES[self.strategy_key]["name"],
            "trading_mode": mode_key,
            "risk_mode": self.risk_mode,
            "direction": direction,
            "asset": token,
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "position_size": pos_size,
            "capital_before": self.capital,
            "open_tick": tick,
            "open_time": datetime.now(timezone.utc).isoformat(),
            "confirms": confirms,
        }
        self.open_trades.append(trade)
        emoji = "📉" if direction == "SHORT" else "📈"
        log.info(f"[{self.name}] {emoji} {direction} {token} @ {entry:.4f} "
                 f"| Mode={mode_key} Risk={self.risk_mode} Conf={confirms} Pos=${pos_size:.0f}")

    def check_exits(self, prices_map, tick):
        closed = []
        for trade in self.open_trades:
            token = trade["asset"]
            curr_price = prices_map.get(token)
            if curr_price is None:
                continue
            mode = TRADING_MODES[trade["trading_mode"]]
            timeout = mode["timeout"]
            age = tick - trade["open_tick"]
            direction = trade["direction"]
            outcome = None
            close_reason = None
            exit_price = curr_price

            if direction == "SHORT":
                if curr_price <= trade["take_profit"]:
                    outcome = "WIN"; close_reason = "TP_HIT"
                elif curr_price >= trade["stop_loss"]:
                    outcome = "LOSS"; close_reason = "SL_HIT"
            else:  # LONG
                if curr_price >= trade["take_profit"]:
                    outcome = "WIN"; close_reason = "TP_HIT"
                elif curr_price <= trade["stop_loss"]:
                    outcome = "LOSS"; close_reason = "SL_HIT"

            if outcome is None and age >= timeout:
                # Force close at current price
                if direction == "SHORT":
                    outcome = "WIN" if curr_price < trade["entry_price"] else "LOSS"
                else:
                    outcome = "WIN" if curr_price > trade["entry_price"] else "LOSS"
                close_reason = "TIMEOUT"
                exit_price = curr_price

            if outcome is not None:
                if direction == "SHORT":
                    pnl = (trade["entry_price"] - exit_price) / trade["entry_price"] * trade["position_size"]
                else:
                    pnl = (exit_price - trade["entry_price"]) / trade["entry_price"] * trade["position_size"]
                pnl = round(pnl, 4)
                pnl_pct = pnl / self.capital * 100
                self.capital += pnl
                self.capital = max(self.capital, 1.0)
                # Cold wallet
                if self.capital - STARTING_CAPITAL >= COLD_WALLET_THRESHOLD:
                    secured = self.capital - STARTING_CAPITAL - COLD_WALLET_THRESHOLD * 0.5
                    if secured > 0:
                        self.cold_wallet += secured
                        self.capital -= secured
                if outcome == "WIN":
                    self.wins += 1
                else:
                    self.losses += 1
                # ── Anti-Martingale: update win streak on trade close ──
                if outcome == "WIN":
                    prev_level = self.doubling_level
                    if self.doubling_level < 3:
                        self.doubling_level += 1
                    self.doubling_active = self.doubling_level > 0
                    self.doubling_wins += 1
                    self.doubling_profit += pnl
                    new_mult = min(2 ** self.doubling_level, 8)
                    if self.doubling_level == 3 and prev_level == 3:
                        # Already at max — record a completed 8x cycle
                        self.doubling_8x_cycles += 1
                        self.doubling_8x_last_tick = tick
                        self.doubling_8x_last_profit = self.doubling_profit
                        log.info(f"[{self.name}] 🎉 ANTI-MARTINGALE 8x CYCLE! "
                                 f"cycle=#{self.doubling_8x_cycles} "
                                 f"profit=${self.doubling_profit:+.2f}")
                    else:
                        log.info(f"[{self.name}] ⬆️ ANTI-MARTINGALE WIN streak={self.doubling_level} "
                                 f"next={new_mult}x profit=${self.doubling_profit:+.2f}")
                elif outcome == "LOSS":
                    if self.doubling_level > 0:
                        log.info(f"[{self.name}] 🔄 ANTI-MARTINGALE RESET — loss resets streak "
                                 f"(was {self.doubling_level}x, profit=${self.doubling_profit:+.2f})")
                    self.doubling_losses += 1
                    self.doubling_active = False
                    self.doubling_level = 0
                    self.doubling_last_loss_tick = tick
                # ──────────────────────────────────────────────────────────────────
                trade.update({
                    "exit_price": exit_price,
                    "capital_after": self.capital,
                    "pnl_usd": pnl,
                    "pnl_pct": pnl_pct,
                    "outcome": outcome,
                    "close_reason": close_reason,
                    "close_tick": tick,
                    "close_time": datetime.now(timezone.utc).isoformat(),
                })
                emoji = "✅" if outcome == "WIN" else "❌"
                log.info(f"[{self.name}] {emoji} {outcome} {token} {direction} "
                         f"PnL=${pnl:+.2f} ({close_reason}) Capital=${self.capital:.2f}")
                save_trade(trade)
                self.closed_trades.append(trade)
                closed.append(trade)
        for t in closed:
            self.open_trades.remove(t)
        self.check_halt()

# ─────────────────────────────────────────────
# TRADING GURU — SELF-LEARNING MASTER
# ─────────────────────────────────────────────
class TradingGuru(Agent):
    def __init__(self, session_id):
        super().__init__("TRADING GURU", "EMA_CROSSOVER", "BALANCED", session_id)
        self.trading_mode = "SCALP_SHORT"  # default trading mode
        self.learning_log = []
        self.knowledge_base = self._load_kb()

    def _load_kb(self):
        if os.path.exists(KB_PATH):
            try:
                with open(KB_PATH) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"patterns": [], "best_combos": {}}

    def _save_kb(self):
        with open(KB_PATH, "w") as f:
            json.dump(self.knowledge_base, f, indent=2)

    def self_learn(self, all_agents: List[Agent], tick: int):
        """Observe all agents and adopt the best PROFITABLE strategy+mode+risk combo.

        SHORT-only enforcement: never adopt a strategy whose only modes are LONG;
        always pick a SHORT-capable trading_mode; refuse to switch to a strategy
        of an agent that is currently underwater.
        """
        best_agent = None
        best_score = -999
        for agent in all_agents:
            if agent.name == self.name or agent.total_trades < 5:
                continue
            # Skip losing agents — only learn from agents currently making money
            if agent.capital + agent.cold_wallet <= STARTING_CAPITAL:
                continue
            # Skip strategies that have no SHORT-capable trading mode
            cand_modes = STRATEGIES[agent.strategy_key].get("modes", [])
            if SHORT_ONLY and not any(
                TRADING_MODES[m]["direction"] in ("SHORT", "BOTH")
                for m in cand_modes
            ):
                continue
            score = agent.win_rate * 100 + (agent.capital - STARTING_CAPITAL) * 0.1
            if score > best_score:
                best_score = score
                best_agent = agent
        if best_agent is None:
            return
        if best_agent.strategy_key != self.strategy_key or best_agent.risk_mode != self.risk_mode:
            old_strat = self.strategy_key
            old_risk = self.risk_mode
            self.strategy_key = best_agent.strategy_key
            self.risk_mode = best_agent.risk_mode
            # Adopt a SHORT-capable trading mode (never LONG)
            best_modes = STRATEGIES[self.strategy_key].get("modes", ["SCALP_SHORT"])
            short_capable = [m for m in best_modes
                             if TRADING_MODES[m]["direction"] in ("SHORT", "BOTH")] or ["SCALP_SHORT"]
            src_mode = getattr(best_agent, 'trading_mode', None)
            if src_mode in short_capable:
                self.trading_mode = src_mode
            else:
                self.trading_mode = short_capable[0]
            event = {
                "tick": tick,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "adopted_strategy": STRATEGIES[self.strategy_key]["name"],
                "adopted_from": best_agent.name,
                "win_rate": best_agent.win_rate,
                "reason": f"Score={best_score:.1f} WR={best_agent.win_rate:.1%} Cap=${best_agent.capital:.2f}"
            }
            self.learning_log.append(event)
            self.knowledge_base["patterns"].append(event)
            self.knowledge_base["best_combos"][self.strategy_key] = {
                "risk": self.risk_mode,
                "win_rate": best_agent.win_rate,
                "tick": tick
            }
            self._save_kb()
            log.info(f"[GURU SELF-LEARNING] 🧠 Adopted {STRATEGIES[self.strategy_key]['name']} "
                     f"from {best_agent.name} (WR={best_agent.win_rate:.1%}) "
                     f"| Risk: {old_risk} → {self.risk_mode}")
            # Save to DB
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""INSERT INTO learning_events
                (session_id,tick,event_time,source_agent,adopted_strategy,adopted_mode,source_win_rate,source_trades,guru_win_rate_before,notes,timestamp,adopted_risk_mode)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (self.session_id, tick, event["timestamp"],
                 event["adopted_from"], event["adopted_strategy"],
                 self.trading_mode, event["win_rate"],
                 best_agent.total_trades, self.win_rate,
                 event["reason"], event["timestamp"], self.risk_mode))
            conn.commit()
            conn.close()

# ─────────────────────────────────────────────
# MARKET DATA
# ─────────────────────────────────────────────
class MarketData:
    # Tokens that are unreliable / zero-priced on OKX from this IP and need a
    # secondary feed (Gate.io public ticker, no API key required).
    GATE_FALLBACK_TOKENS = ("SHIB/USDT", "PEPE/USDT", "FLOKI/USDT",
                            "BONK/USDT", "BOME/USDT")

    def __init__(self):
        self.exchange = ccxt.okx({"enableRateLimit": True, "timeout": 10000})
        # Public Gate.io spot client — used as a fallback only for the small
        # set of tokens we know OKX returns 0 / null prices for.
        try:
            self.gate = ccxt.gateio({"enableRateLimit": True, "timeout": 10000})
        except Exception:
            self.gate = None
        self.prices: Dict[str, deque] = {t: deque(maxlen=100) for t in ALL_TOKENS}
        self.current_prices: Dict[str, float] = {}
        self.available_tokens = []
        self.fallback_hits: Dict[str, int] = {}
        # Last UTC ISO timestamp at which a Gate.io fallback price was actually used
        self.last_fallback_at: Optional[str] = None
        # Set of tokens that fell back on the most recent fetch_prices() tick
        self.last_fallback_tokens: List[str] = []

    def _fetch_from_gate(self, token: str) -> Optional[float]:
        """Best-effort public Gate.io price; returns None if unavailable."""
        if not self.gate:
            return None
        try:
            ticker = self.gate.fetch_ticker(token)
            last = ticker.get("last") if ticker else None
            if last and float(last) > MIN_PRICE_FLOOR:
                return float(last)
        except Exception:
            return None
        return None

    async def probe_tokens(self):
        """Find which tokens are actually available on OKX — with retry logic
        and a Gate.io fallback for the meme/illiquid tokens that OKX returns 0 for."""
        available = []
        for token in ALL_TOKENS:
            got_price = False
            for attempt in range(3):
                try:
                    ticker = self.exchange.fetch_ticker(token)
                    last = ticker.get("last") if ticker else None
                    if last and float(last) > MIN_PRICE_FLOOR:
                        available.append(token)
                        self.current_prices[token] = float(last)
                        self.prices[token].append(float(last))
                        got_price = True
                    await asyncio.sleep(0.08)
                    break
                except Exception:
                    if attempt < 2:
                        await asyncio.sleep(1)
            # Try Gate.io fallback for known-offline tokens
            if not got_price and token in self.GATE_FALLBACK_TOKENS:
                px = self._fetch_from_gate(token)
                if px:
                    available.append(token)
                    self.current_prices[token] = px
                    self.prices[token].append(px)
                    self.fallback_hits[token] = self.fallback_hits.get(token, 0) + 1
                    log.info(f"[MARKET] 🔄 Gate.io fallback used for {token} @ {px}")
        self.available_tokens = available if available else list(self.current_prices.keys()) or ALL_TOKENS[:5]
        log.info(f"[MARKET] ✅ {len(available)}/{len(ALL_TOKENS)} tokens available "
                 f"(OKX + Gate fallback) | fallback_hits={self.fallback_hits}")
        return available

    async def fetch_prices(self):
        """Fetch all token prices with auto-retry, OKX primary + Gate fallback,
        and only drop tokens that are unreachable on BOTH exchanges."""
        updated = 0
        failed = []
        tick_fallback_tokens: List[str] = []
        for token in self.available_tokens:
            got_price = False
            for attempt in range(MAX_RETRIES):
                try:
                    ticker = self.exchange.fetch_ticker(token)
                    last = ticker.get("last") if ticker else None
                    if last and float(last) > MIN_PRICE_FLOOR:
                        price = float(last)
                        self.current_prices[token] = price
                        self.prices[token].append(price)
                        updated += 1
                        got_price = True
                    await asyncio.sleep(0.04)
                    break
                except ccxt.NetworkError:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                except ccxt.ExchangeError:
                    break
                except Exception:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(1)
            # Gate.io fallback for tokens that OKX cannot price
            if not got_price and token in self.GATE_FALLBACK_TOKENS:
                px = self._fetch_from_gate(token)
                if px:
                    self.current_prices[token] = px
                    self.prices[token].append(px)
                    updated += 1
                    got_price = True
                    self.fallback_hits[token] = self.fallback_hits.get(token, 0) + 1
                    tick_fallback_tokens.append(token)
            if not got_price:
                failed.append(token)
        # Record fallback usage for this tick (consumed by save_state → UI)
        self.last_fallback_tokens = tick_fallback_tokens
        if tick_fallback_tokens:
            self.last_fallback_at = datetime.now(timezone.utc).isoformat()
        # Remove persistently failing tokens from available list (only if both
        # primary and fallback failed for this tick).
        if failed:
            for t in failed:
                if t in self.available_tokens:
                    self.available_tokens.remove(t)
            log.warning(f"[MARKET] ⚠️ Removed {len(failed)} unavailable tokens (OKX+Gate both failed)")
        return updated

    async def reconnect(self):
        """Reconnect to OKX exchange after connection failure"""
        log.warning("[MARKET] 🔄 Reconnecting to OKX...")
        for attempt in range(10):
            try:
                self.exchange = ccxt.okx({"enableRateLimit": True, "timeout": 15000})
                await self.probe_tokens()
                log.info(f"[MARKET] ✅ Reconnected — {len(self.available_tokens)} tokens")
                return True
            except Exception as e:
                log.warning(f"[MARKET] Reconnect attempt {attempt+1}/10 failed: {e}")
                await asyncio.sleep(10 * (attempt + 1))
        log.error("[MARKET] ❌ All reconnect attempts failed — will retry next tick")
        return False

# ─────────────────────────────────────────────
# LEADERBOARD
# ─────────────────────────────────────────────
def print_leaderboard(agents: List[Agent], tick: int):
    sorted_agents = sorted(agents, key=lambda a: a.capital + a.cold_wallet, reverse=True)
    log.info(f"\n{'='*80}")
    log.info(f"  LEADERBOARD — Tick #{tick} — {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
    log.info(f"{'='*80}")
    log.info(f"  {'#':<3} {'Agent':<18} {'Strategy':<30} {'Capital':>9} {'CW':>8} {'WR':>7} {'W/L':>8} {'Risk':<6}")
    log.info(f"  {'-'*90}")
    for i, a in enumerate(sorted_agents, 1):
        rm = RISK_MODES[a.risk_mode]
        status = "⛔HALT" if a.halted else "🟢LIVE"
        log.info(f"  {i:<3} {a.name:<18} {STRATEGIES[a.strategy_key]['name']:<30} "
                 f"${a.capital:>8.2f} ${a.cold_wallet:>7.2f} {a.win_rate:>6.1%} "
                 f"{a.wins:>4}W/{a.losses:<4}L {rm['emoji']}{a.risk_mode:<14} {status}")
    log.info(f"{'='*80}\n")

def save_state(agents: List[Agent], tick: int, session_id: str, prices_map: dict = None,
               market: Optional['MarketData'] = None):
    state = {
        "version": VERSION,
        "session_id": session_id,
        "tick": tick,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategies_count": len(STRATEGIES),
        "agents_count": len(agents),
        "prices": {k: round(v, 4) for k, v in (prices_map or {}).items()},
        # Gate.io fallback telemetry consumed by the dashboard / UI indicator
        "fallback": {
            "watched_tokens": list(MarketData.GATE_FALLBACK_TOKENS),
            "hits": dict(market.fallback_hits) if market else {},
            "last_active_at": (market.last_fallback_at if market else None),
            "last_active_tokens": list(market.last_fallback_tokens) if market else [],
            "active_now": bool(market and market.last_fallback_tokens),
        },
        "agents": []
    }
    for a in agents:
        rm = RISK_MODES[a.risk_mode]
        state["agents"].append({
            "name": a.name,
            "strategy": STRATEGIES[a.strategy_key]["name"],
            "strategy_key": a.strategy_key,
            "risk_mode": a.risk_mode,
            "risk_emoji": rm["emoji"],
            "capital": round(a.capital, 2),
            "cold_wallet": round(a.cold_wallet, 2),
            "total": round(a.capital + a.cold_wallet, 2),
            "wins": a.wins,
            "losses": a.losses,
            "win_rate": round(a.win_rate * 100, 1),
            "open_trades": len(a.open_trades),
            "halted": a.halted,
            # Anti-Martingale System state (field names kept for dashboard compat)
            "doubling_active": a.doubling_active,
            "doubling_level": a.doubling_level,
            "doubling_mult": min(2 ** a.doubling_level, 8) if a.doubling_level > 0 else 1,
            "doubling_wins": a.doubling_wins,
            "doubling_losses": a.doubling_losses,
            "doubling_profit": round(a.doubling_profit, 2),
        })
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)

# ─────────────────────────────────────────────
# MAIN ENGINE LOOP
# ─────────────────────────────────────────────
async def run_engine():
    session_id = f"v9_{int(time.time())}"
    log.info(f"{'='*80}")
    log.info(f"  Trading Strategies Testing Engine {VERSION} — UNSTOPPABLE 24/7")
    log.info(f"  Session: {session_id}")
    log.info(f"  Strategies: {len(STRATEGIES)} | Agents: {len(AGENT_CONFIGS)}")
    log.info(f"  Modes: {len(TRADING_MODES)} | Risk Profiles: {len(RISK_MODES)}")
    log.info(f"  Tokens: {len(ALL_TOKENS)} across 4 tiers (PAPER MODE — OKX real data)")
    log.info(f"{'='*80}")

    init_db()
    market = MarketData()

    # Probe available tokens with retry
    log.info("[MARKET] Probing OKX token availability...")
    for probe_attempt in range(5):
        await market.probe_tokens()
        if market.available_tokens:
            break
        log.warning(f"[MARKET] Probe attempt {probe_attempt+1}/5 failed, retrying in 10s...")
        await asyncio.sleep(10)

    if not market.available_tokens:
        log.error("[MARKET] Could not connect to OKX — using fallback token list")
        market.available_tokens = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "AVAX/USDT"]

    # Create agents
    agents: List[Agent] = []
    guru = None
    for cfg in AGENT_CONFIGS:
        if cfg["name"] == "TRADING GURU":
            guru = TradingGuru(session_id)
            agents.append(guru)
        else:
            agents.append(Agent(cfg["name"], cfg["strategy"], cfg["risk"], session_id))

    log.info(f"[ENGINE] {len(agents)} agents initialized — ALL TRADING 24/7")
    log.info(f"[ENGINE] Available tokens: {len(market.available_tokens)} — {market.available_tokens[:5]}...")

    tick = 0
    start_time = time.time()
    consecutive_failures = 0

    while True:  # INFINITE LOOP — NEVER STOPS
        tick_start = time.time()
        tick += 1

        # ── FETCH PRICES ──────────────────────────────────────────────────────
        try:
            updated = await market.fetch_prices()
        except Exception as e:
            log.error(f"[Tick #{tick}] fetch_prices crashed: {e}")
            updated = 0

        if updated == 0:
            consecutive_failures += 1
            log.warning(f"[Tick #{tick}] No prices fetched (failures={consecutive_failures}) — retrying...")
            if consecutive_failures >= 3:
                log.warning("[ENGINE] 3 consecutive failures — attempting reconnect...")
                await market.reconnect()
                consecutive_failures = 0
            await asyncio.sleep(TICK_INTERVAL)
            continue
        else:
            consecutive_failures = 0

        prices_map = market.current_prices

        # ── RE-PROBE TOKENS PERIODICALLY ─────────────────────────────────────
        if tick % REPROBE_EVERY == 0:
            log.info(f"[ENGINE] Re-probing OKX tokens at tick #{tick}...")
            await market.probe_tokens()
            log.info(f"[ENGINE] Token list updated: {len(market.available_tokens)} tokens")

        # ── AGENT TRADING LOOP ────────────────────────────────────────────────
        for agent in agents:
            try:
                agent.adapt_risk_mode(tick)
                for token in market.available_tokens:
                    prices_list = list(market.prices[token])
                    if len(prices_list) >= 5:
                        agent.try_open_trade(token, prices_list, tick)
                agent.check_exits(prices_map, tick)
            except Exception as e:
                log.error(f"[{agent.name}] Agent loop error: {e} — continuing")
                continue  # Never stop for a single agent error

        # ── GURU SELF-LEARNING ────────────────────────────────────────────────
        if guru and tick % GURU_LEARN_EVERY == 0:
            try:
                guru.self_learn([a for a in agents if a.name != "TRADING GURU"], tick)
            except Exception as e:
                log.error(f"[GURU] self_learn error: {e} — continuing")

        # ── CROSS-AGENT BROADCAST (Self-Upgrading Ecosystem) ─────────────────
        # Every 25 ticks: Guru broadcasts its best combo to bottom-25% agents
        if guru and tick % 25 == 0 and tick > 0:
            try:
                kb = guru.knowledge_base.get("best_combos", {})
                if kb:
                    # Find best combo by win_rate
                    best_combo_key = max(kb, key=lambda k: kb[k].get("win_rate", 0))
                    best_combo = kb[best_combo_key]
                    # Identify bottom 25% agents by total_value
                    sorted_agents = sorted(
                        [a for a in agents if a.name != "TRADING GURU"],
                        key=lambda a: a.capital + a.cold_wallet
                    )
                    bottom_count = max(1, len(sorted_agents) // 4)
                    bottom_agents = sorted_agents[:bottom_count]
                    upgraded = 0
                    for agent in bottom_agents:
                        # Only upgrade if agent is losing (below starting capital)
                        if agent.capital + agent.cold_wallet < STARTING_CAPITAL * 0.95:
                            old_strat = agent.strategy_key
                            agent.strategy_key = best_combo_key
                            agent.risk_mode = best_combo.get("risk", "BALANCED")
                            # Assign a SHORT-capable mode
                            best_modes = STRATEGIES[best_combo_key].get("modes", ["SCALP_SHORT"])
                            short_modes = [m for m in best_modes
                                           if TRADING_MODES[m]["direction"] in ("SHORT", "BOTH")]
                            if short_modes:
                                agent.trading_mode = short_modes[0]
                            upgraded += 1
                            log.info(f"[BROADCAST] 📡 {agent.name} upgraded: "
                                     f"{old_strat} → {best_combo_key} "
                                     f"(WR={best_combo.get('win_rate', 0):.1%})"
                            )
                    if upgraded > 0:
                        log.info(f"[BROADCAST] 🤖 Upgraded {upgraded} bottom agents with Guru knowledge")
            except Exception as e:
                log.error(f"[BROADCAST] Error: {e} — continuing")

        # ── LEADERBOARD ───────────────────────────────────────────────────────
        if tick % 20 == 0:
            try:
                print_leaderboard(agents, tick)
            except Exception as e:
                log.error(f"[LEADERBOARD] Error: {e}")

        # ── STATE SAVE ────────────────────────────────────────────────────────
        if tick % STATE_SAVE_EVERY == 0:
            try:
                save_state(agents, tick, session_id, prices_map, market)
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                ts = datetime.now(timezone.utc).isoformat()
                for rank_idx, a in enumerate(sorted(agents, key=lambda x: x.capital, reverse=True), 1):
                    c.execute("""INSERT INTO agent_snapshots
                        (session_id,tick,snapshot_time,agent_name,strategy,trading_mode,capital,cold_wallet,
                         total_value,wins,losses,win_rate,total_trades,rank) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (session_id, tick, ts, a.name, STRATEGIES[a.strategy_key]["name"],
                         getattr(a, 'trading_mode', a.strategy_key), a.capital, a.cold_wallet,
                         a.capital + a.cold_wallet, a.wins, a.losses, a.win_rate,
                         a.total_trades, rank_idx))
                conn.commit()
                conn.close()
            except Exception as e:
                log.error(f"[STATE] Save error: {e} — continuing")

        # ── TICK SUMMARY ──────────────────────────────────────────────────────
        total_open = sum(len(a.open_trades) for a in agents)
        total_closed = sum(a.total_trades for a in agents)
        active_agents = sum(1 for a in agents if not a.halted)
        elapsed = time.time() - start_time
        log.info(f"[Tick #{tick}] Prices={updated} Tokens={len(market.available_tokens)} "
                 f"Open={total_open} Closed={total_closed} Active={active_agents}/31 "
                 f"Uptime={elapsed/3600:.1f}h")

        # ── SLEEP ─────────────────────────────────────────────────────────────
        elapsed_tick = time.time() - tick_start
        sleep_time = max(0, TICK_INTERVAL - elapsed_tick)
        await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    while True:  # Outer loop: restart engine on any unhandled crash
        try:
            asyncio.run(run_engine())
        except KeyboardInterrupt:
            log.info("[ENGINE] Keyboard interrupt — shutting down")
            break
        except Exception as e:
            log.error(f"[ENGINE] CRITICAL CRASH: {e} — restarting in 10s...")
            time.sleep(10)
