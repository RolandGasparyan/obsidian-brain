#!/usr/bin/env python3
"""
Trading Strategies Testing Engine v2.0
=======================================
8 Momentum Scalping Strategies | 8 Specialized Agents + Trading Guru Master
24/7 Self-Learning | Real Market Data (Binance) | Paper Trading | SHORT ONLY
Assets: XRP, AVAX, SOL, BTC, ETH
Gods Level Position Sizing: POSITION = RISK ÷ STOP% × 0.25 (Kelly)
"""

import asyncio
import json
import time
import random
import math
import logging
import os
from datetime import datetime, timezone
from collections import deque
import ccxt

# ─── CONFIG ──────────────────────────────────────────────────────────────────
ASSETS = ["XRP/USDT", "AVAX/USDT", "SOL/USDT", "BTC/USDT", "ETH/USDT"]
ASSETS_KRAKEN = ["XRP/USD", "AVAX/USD", "SOL/USD", "BTC/USD", "ETH/USD"]
ASSET_MAP_KRAKEN = {"XRP/USDT": "XRP/USD", "AVAX/USDT": "AVAX/USD", "SOL/USDT": "SOL/USD", "BTC/USDT": "BTC/USD", "ETH/USDT": "ETH/USD"}
STARTING_CAPITAL = 1000.0
RISK_PER_TRADE = 0.02          # 2% risk per trade
KELLY_FACTOR = 0.25            # Quarter Kelly
COLD_WALLET_THRESHOLD = 100.0  # Secure profits above $100
LOG_FILE = "/home/ubuntu/trading_engine/engine.log"
KB_FILE = "/home/ubuntu/trading_engine/knowledge_base.json"
STATE_FILE = "/home/ubuntu/trading_engine/engine_state.json"
TICK_INTERVAL = 8              # seconds between ticks
MIN_HISTORY = 20               # minimum candles before trading

# ATR volatility floors per asset (% of price)
ATR_FLOORS = {
    "XRP/USDT": 0.008,
    "AVAX/USDT": 0.012,
    "SOL/USDT": 0.012,
    "BTC/USDT": 0.006,
    "ETH/USDT": 0.008,
}

# ─── LOGGING ─────────────────────────────────────────────────────────────────
os.makedirs("/home/ubuntu/trading_engine", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("TradingEngine")

# ─── STRATEGY DEFINITIONS ────────────────────────────────────────────────────
STRATEGIES = {
    "EMA_CROSS": {
        "name": "EMA 9/21 Crossover",
        "description": "9 EMA crosses below 21 EMA → SHORT signal. Fast momentum flip detection.",
        "timeframe": "1m",
        "indicators": ["EMA9", "EMA21", "RSI14", "VWAP"],
        "min_confirm": 3,
    },
    "VWAP_MACD": {
        "name": "VWAP + MACD Momentum",
        "description": "Price breaks below VWAP + MACD histogram turns negative → SHORT.",
        "timeframe": "1m",
        "indicators": ["VWAP", "MACD", "EMA9", "Volume"],
        "min_confirm": 3,
    },
    "KELTNER_RSI": {
        "name": "Keltner Channel + RSI",
        "description": "2+ closes outside upper Keltner Band + RSI > 70 → SHORT reversal.",
        "timeframe": "5m",
        "indicators": ["Keltner", "RSI14", "ATR", "EMA20"],
        "min_confirm": 3,
    },
    "BB_SQUEEZE": {
        "name": "Bollinger Band Squeeze Breakout",
        "description": "BB squeeze (low volatility) → breakout below lower band → SHORT.",
        "timeframe": "5m",
        "indicators": ["BB_Upper", "BB_Lower", "BB_Width", "RSI4"],
        "min_confirm": 3,
    },
    "SUPERTREND_MACD": {
        "name": "SuperTrend + MACD",
        "description": "SuperTrend flips bearish + MACD crosses below signal → SHORT.",
        "timeframe": "5m",
        "indicators": ["SuperTrend", "MACD", "ATR", "Volume"],
        "min_confirm": 3,
    },
    "ORDER_FLOW": {
        "name": "Order Flow Imbalance",
        "description": "Ask/Bid ratio > 2.0 (heavy sell pressure) + CVD divergence → SHORT.",
        "timeframe": "1m",
        "indicators": ["OrderBook", "CVD", "Delta", "Volume"],
        "min_confirm": 3,
    },
    "PIVOT_BREAKOUT": {
        "name": "Pivot Point Breakdown",
        "description": "Price breaks below daily pivot + RSI < 50 + volume spike → SHORT.",
        "timeframe": "5m",
        "indicators": ["Pivot", "R1", "S1", "RSI14", "Volume"],
        "min_confirm": 3,
    },
    "ALMA_STOCH": {
        "name": "ALMA + Stochastic Reversal",
        "description": "Price closes below ALMA + Stochastic crosses below 80 → SHORT reversal.",
        "timeframe": "1m",
        "indicators": ["ALMA21", "Stochastic", "ATR", "EMA9"],
        "min_confirm": 3,
    },
}

# ─── INDICATOR COMPUTATIONS ──────────────────────────────────────────────────

def ema(prices, period):
    if len(prices) < period:
        return None
    k = 2.0 / (period + 1)
    val = sum(prices[:period]) / period
    for p in prices[period:]:
        val = p * k + val * (1 - k)
    return val

def sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return sum(trs[-period:]) / period

def bollinger(prices, period=20, std_dev=2.0):
    if len(prices) < period:
        return None, None, None
    mid = sma(prices, period)
    variance = sum((p - mid) ** 2 for p in prices[-period:]) / period
    std = math.sqrt(variance)
    return mid - std_dev * std, mid, mid + std_dev * std

def macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow + signal:
        return None, None, None
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    if ema_fast is None or ema_slow is None:
        return None, None, None
    macd_line = ema_fast - ema_slow
    # Approximate signal line
    macd_vals = []
    for i in range(slow, len(prices)):
        ef = ema(prices[:i+1], fast)
        es = ema(prices[:i+1], slow)
        if ef and es:
            macd_vals.append(ef - es)
    if len(macd_vals) < signal:
        return macd_line, None, None
    signal_line = ema(macd_vals, signal)
    histogram = macd_line - signal_line if signal_line else None
    return macd_line, signal_line, histogram

def supertrend(highs, lows, closes, period=10, multiplier=3.0):
    if len(closes) < period + 1:
        return None, None
    atr_val = atr(highs, lows, closes, period)
    if atr_val is None:
        return None, None
    price = closes[-1]
    mid = (highs[-1] + lows[-1]) / 2
    upper = mid + multiplier * atr_val
    lower = mid - multiplier * atr_val
    # Simplified: bearish if price < lower band midpoint
    bearish = price < (upper + lower) / 2
    return bearish, atr_val

def stochastic(highs, lows, closes, k_period=14, d_period=3):
    if len(closes) < k_period:
        return None, None
    lowest = min(lows[-k_period:])
    highest = max(highs[-k_period:])
    if highest == lowest:
        return 50.0, 50.0
    k = 100 * (closes[-1] - lowest) / (highest - lowest)
    # Approximate D as simple average of last d_period K values
    k_vals = []
    for i in range(d_period):
        idx = -(i + 1)
        lo = min(lows[max(0, len(lows) + idx - k_period):len(lows) + idx + 1])
        hi = max(highs[max(0, len(highs) + idx - k_period):len(highs) + idx + 1])
        c = closes[len(closes) + idx]
        if hi != lo:
            k_vals.append(100 * (c - lo) / (hi - lo))
    d = sum(k_vals) / len(k_vals) if k_vals else k
    return k, d

def alma(prices, window=21, offset=0.85, sigma=6):
    if len(prices) < window:
        return None
    m = offset * (window - 1)
    s = window / sigma
    weights = [math.exp(-((i - m) ** 2) / (2 * s * s)) for i in range(window)]
    w_sum = sum(weights)
    recent = prices[-window:]
    return sum(recent[i] * weights[i] for i in range(window)) / w_sum

def vwap_approx(prices, volumes):
    if not volumes or sum(volumes) == 0:
        return prices[-1]
    return sum(p * v for p, v in zip(prices, volumes)) / sum(volumes)

def pivot_points(high, low, close):
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    return pivot, r1, s1

# ─── POSITION SIZING (GODS LEVEL) ────────────────────────────────────────────

def gods_level_position(capital, price, asset, confidence_score, max_score):
    risk_dollar = capital * RISK_PER_TRADE
    base_atr_pct = ATR_FLOORS.get(asset, 0.01)
    # Confidence multiplier: higher confidence → tighter stop (bigger position)
    conf_ratio = confidence_score / max_score if max_score > 0 else 0.5
    stop_pct = base_atr_pct * (1.0 + (1.0 - conf_ratio) * 0.5)
    stop_pct = max(stop_pct, ATR_FLOORS.get(asset, 0.006))
    base_position = risk_dollar / stop_pct
    final_position = base_position * KELLY_FACTOR
    units = final_position / price
    stop_price = price * (1 + stop_pct)   # SHORT: stop ABOVE entry
    tp_price = price * (1 - stop_pct * 2) # 2:1 R:R take-profit BELOW entry
    return {
        "position_usd": round(final_position, 2),
        "units": round(units, 6),
        "stop_pct": round(stop_pct * 100, 3),
        "stop_price": round(stop_price, 6),
        "tp_price": round(tp_price, 6),
        "risk_usd": round(risk_dollar, 2),
    }

# ─── STRATEGY SIGNAL GENERATORS ──────────────────────────────────────────────

def signal_ema_cross(prices, highs, lows, volumes):
    """EMA 9/21 Crossover SHORT signal"""
    if len(prices) < 25:
        return 0, []
    e9 = ema(prices, 9)
    e21 = ema(prices, 21)
    e9_prev = ema(prices[:-1], 9)
    e21_prev = ema(prices[:-1], 21)
    rsi_val = rsi(prices, 14)
    vwap = vwap_approx(prices[-20:], volumes[-20:] if volumes else [1]*20)
    confirms = []
    if e9 and e21 and e9_prev and e21_prev:
        if e9 < e21 and e9_prev >= e21_prev:
            confirms.append("EMA9 crossed below EMA21")
        elif e9 < e21:
            confirms.append("EMA9 below EMA21 (bearish)")
    if rsi_val and rsi_val > 55:
        confirms.append(f"RSI={rsi_val:.1f} elevated (momentum)")
    if prices[-1] < vwap:
        confirms.append("Price below VWAP (bearish bias)")
    if len(prices) >= 3 and prices[-1] < prices[-2] < prices[-3]:
        confirms.append("3-candle bearish sequence")
    return len(confirms), confirms

def signal_vwap_macd(prices, highs, lows, volumes):
    """VWAP + MACD SHORT signal"""
    if len(prices) < 35:
        return 0, []
    vwap = vwap_approx(prices[-20:], volumes[-20:] if volumes else [1]*20)
    macd_line, sig_line, histogram = macd(prices)
    confirms = []
    if prices[-1] < vwap:
        confirms.append("Price below VWAP")
    if macd_line and sig_line:
        if macd_line < sig_line:
            confirms.append("MACD below signal line")
        if histogram and histogram < 0:
            confirms.append("MACD histogram negative")
    if len(prices) >= 2 and prices[-1] < prices[-2]:
        confirms.append("Bearish candle close")
    if volumes and len(volumes) >= 5:
        avg_vol = sum(volumes[-5:]) / 5
        if volumes[-1] > avg_vol * 1.3:
            confirms.append("Volume spike on down move")
    return len(confirms), confirms

def signal_keltner_rsi(prices, highs, lows, volumes):
    """Keltner Channel + RSI SHORT signal"""
    if len(prices) < 22:
        return 0, []
    atr_val = atr(highs, lows, prices, 14)
    e20 = ema(prices, 20)
    rsi_val = rsi(prices, 14)
    confirms = []
    if atr_val and e20:
        upper_keltner = e20 + 2 * atr_val
        if prices[-1] > upper_keltner:
            confirms.append("Price above upper Keltner Band (overbought)")
        if len(prices) >= 2 and prices[-2] > (e20 + 2 * atr_val):
            confirms.append("2nd close above Keltner (reversal zone)")
    if rsi_val and rsi_val > 65:
        confirms.append(f"RSI={rsi_val:.1f} overbought")
    if atr_val and e20 and prices[-1] > e20:
        confirms.append("Price extended above EMA20")
    return len(confirms), confirms

def signal_bb_squeeze(prices, highs, lows, volumes):
    """Bollinger Band Squeeze Breakout SHORT signal"""
    if len(prices) < 22:
        return 0, []
    lower, mid, upper = bollinger(prices, 20, 2.0)
    rsi_val = rsi(prices, 4)
    confirms = []
    if lower and upper and mid:
        bb_width = (upper - lower) / mid
        # Squeeze: width < 2% of price
        if bb_width < 0.02:
            confirms.append(f"BB squeeze detected (width={bb_width*100:.2f}%)")
        if prices[-1] > upper:
            confirms.append("Price above upper BB (overextended)")
        if len(prices) >= 2 and prices[-2] > upper:
            confirms.append("Previous close above upper BB")
    if rsi_val and rsi_val > 75:
        confirms.append(f"RSI(4)={rsi_val:.1f} extreme overbought")
    if len(prices) >= 3 and prices[-1] < prices[-2]:
        confirms.append("Bearish reversal candle")
    return len(confirms), confirms

def signal_supertrend_macd(prices, highs, lows, volumes):
    """SuperTrend + MACD SHORT signal"""
    if len(prices) < 35:
        return 0, []
    bearish_st, atr_val = supertrend(highs, lows, prices, 10, 3.0)
    macd_line, sig_line, histogram = macd(prices)
    confirms = []
    if bearish_st:
        confirms.append("SuperTrend bearish flip")
    if macd_line and sig_line and macd_line < sig_line:
        confirms.append("MACD bearish crossover")
    if histogram and histogram < 0:
        confirms.append("MACD histogram negative momentum")
    if atr_val and len(prices) >= 2:
        move = abs(prices[-1] - prices[-2])
        if move > atr_val * 0.5:
            confirms.append("Strong bearish candle (>0.5 ATR)")
    if volumes and len(volumes) >= 3:
        avg_vol = sum(volumes[-3:]) / 3
        if volumes[-1] > avg_vol * 1.2:
            confirms.append("Volume confirmation")
    return len(confirms), confirms

def signal_order_flow(prices, highs, lows, volumes):
    """Order Flow Imbalance SHORT signal"""
    if len(prices) < 10:
        return 0, []
    confirms = []
    # Simulate order book imbalance using price/volume dynamics
    if volumes and len(volumes) >= 5:
        recent_vols = volumes[-5:]
        avg_vol = sum(recent_vols) / 5
        # High volume on down candles = sell pressure
        down_vol = sum(v for i, v in enumerate(recent_vols) if i > 0 and prices[-(5-i)] < prices[-(5-i+1)])
        up_vol = sum(v for i, v in enumerate(recent_vols) if i > 0 and prices[-(5-i)] >= prices[-(5-i+1)])
        if up_vol > 0 and down_vol / (up_vol + 1) > 1.5:
            confirms.append("CVD divergence: sell volume dominates")
        if recent_vols[-1] > avg_vol * 1.5:
            confirms.append("Volume spike (order flow surge)")
    # Price momentum check
    if len(prices) >= 5:
        recent_move = (prices[-1] - prices[-5]) / prices[-5]
        if recent_move < -0.003:
            confirms.append("Bearish price momentum (-0.3%+)")
        if recent_move > 0.005:
            confirms.append("Price up but volume selling (divergence)")
    rsi_val = rsi(prices, 14)
    if rsi_val and rsi_val > 60:
        confirms.append(f"RSI={rsi_val:.1f} elevated (distribution zone)")
    if len(prices) >= 3 and prices[-1] < prices[-2] < prices[-3]:
        confirms.append("3-bar bearish sequence")
    return len(confirms), confirms

def signal_pivot_breakout(prices, highs, lows, volumes):
    """Pivot Point Breakdown SHORT signal"""
    if len(prices) < 25:
        return 0, []
    # Use last 24h high/low/close for pivot
    day_high = max(highs[-24:]) if len(highs) >= 24 else max(highs)
    day_low = min(lows[-24:]) if len(lows) >= 24 else min(lows)
    day_close = prices[-24] if len(prices) >= 24 else prices[0]
    pivot, r1, s1 = pivot_points(day_high, day_low, day_close)
    rsi_val = rsi(prices, 14)
    confirms = []
    if prices[-1] < pivot:
        confirms.append(f"Price below pivot ({pivot:.4f})")
    if prices[-1] < s1:
        confirms.append(f"Price broke S1 support ({s1:.4f})")
    if rsi_val and rsi_val < 50:
        confirms.append(f"RSI={rsi_val:.1f} below 50 (bearish)")
    if volumes and len(volumes) >= 5:
        avg_vol = sum(volumes[-5:]) / 5
        if volumes[-1] > avg_vol * 1.2:
            confirms.append("Volume spike on breakdown")
    if len(prices) >= 2 and prices[-1] < prices[-2]:
        confirms.append("Bearish candle close")
    return len(confirms), confirms

def signal_alma_stoch(prices, highs, lows, volumes):
    """ALMA + Stochastic Reversal SHORT signal"""
    if len(prices) < 25:
        return 0, []
    alma_val = alma(prices, 21, 0.85, 6)
    k, d = stochastic(highs, lows, prices, 14, 3)
    confirms = []
    if alma_val and prices[-1] < alma_val:
        confirms.append(f"Price below ALMA ({alma_val:.4f})")
    if k and k > 75:
        confirms.append(f"Stochastic K={k:.1f} overbought (>75)")
    if k and d and k < d and k > 70:
        confirms.append("Stochastic bearish cross from overbought")
    if len(prices) >= 2 and prices[-1] < prices[-2]:
        confirms.append("Bearish close below ALMA")
    atr_val = atr(highs, lows, prices, 14)
    if atr_val and len(prices) >= 2:
        move = prices[-2] - prices[-1]
        if move > atr_val * 0.3:
            confirms.append("Bearish candle size > 0.3 ATR")
    return len(confirms), confirms

STRATEGY_SIGNALS = {
    "EMA_CROSS": signal_ema_cross,
    "VWAP_MACD": signal_vwap_macd,
    "KELTNER_RSI": signal_keltner_rsi,
    "BB_SQUEEZE": signal_bb_squeeze,
    "SUPERTREND_MACD": signal_supertrend_macd,
    "ORDER_FLOW": signal_order_flow,
    "PIVOT_BREAKOUT": signal_pivot_breakout,
    "ALMA_STOCH": signal_alma_stoch,
}

# ─── AGENT CLASS ─────────────────────────────────────────────────────────────

class TradingAgent:
    def __init__(self, name, strategy_key, capital=None):
        self.name = name
        self.strategy_key = strategy_key
        self.strategy = STRATEGIES[strategy_key]
        self.capital = capital or STARTING_CAPITAL
        self.cold_wallet = 0.0
        self.open_trades = {}   # asset → trade dict
        self.trade_log = []
        self.wins = 0
        self.losses = 0
        self.total_trades = 0
        self.peak_capital = self.capital
        self.max_drawdown = 0.0
        self.daily_loss = 0.0
        self.daily_loss_limit = self.capital * 0.05  # 5% daily loss stop
        self.halted_today = False
        self.learned_patterns = []  # patterns absorbed from Guru

    @property
    def win_rate(self):
        if self.total_trades == 0:
            return 0.0
        return self.wins / self.total_trades * 100

    @property
    def total_value(self):
        return self.capital + self.cold_wallet

    def check_cold_wallet(self):
        profit = self.capital - STARTING_CAPITAL + self.cold_wallet
        if profit >= COLD_WALLET_THRESHOLD:
            secure = profit - (COLD_WALLET_THRESHOLD * 0.5)
            if secure > 0:
                self.cold_wallet += secure
                self.capital -= secure
                log.info(f"[{self.name}] 💰 COLD WALLET: Secured ${secure:.2f} → Total secured: ${self.cold_wallet:.2f}")

    def update_drawdown(self):
        if self.capital > self.peak_capital:
            self.peak_capital = self.capital
        dd = (self.peak_capital - self.capital) / self.peak_capital * 100
        self.max_drawdown = max(self.max_drawdown, dd)

    def to_dict(self):
        return {
            "name": self.name,
            "strategy": self.strategy["name"],
            "strategy_key": self.strategy_key,
            "capital": round(self.capital, 2),
            "cold_wallet": round(self.cold_wallet, 2),
            "total_value": round(self.total_value, 2),
            "wins": self.wins,
            "losses": self.losses,
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 1),
            "max_drawdown": round(self.max_drawdown, 2),
            "open_trades": len(self.open_trades),
            "halted": self.halted_today,
        }

# ─── TRADING GURU MASTER AGENT ───────────────────────────────────────────────

class TradingGuru(TradingAgent):
    def __init__(self):
        super().__init__("TRADING GURU", "EMA_CROSS")
        self.knowledge_base = self._load_kb()
        self.observed_strategies = {}   # strategy_key → performance stats
        self.active_strategy = "EMA_CROSS"
        self.upgrade_count = 0

    def _load_kb(self):
        if os.path.exists(KB_FILE):
            try:
                with open(KB_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"patterns": [], "strategy_performance": {}, "upgrades": []}

    def _save_kb(self):
        try:
            with open(KB_FILE, "w") as f:
                json.dump(self.knowledge_base, f, indent=2)
        except Exception as e:
            log.warning(f"KB save error: {e}")

    def observe_agents(self, agents):
        """Learn from all peer agents — adopt best performing strategy"""
        best_strategy = None
        best_wr = -1
        for agent in agents:
            if agent.total_trades >= 5:
                stats = {
                    "strategy": agent.strategy_key,
                    "win_rate": agent.win_rate,
                    "total_trades": agent.total_trades,
                    "capital": agent.capital,
                }
                self.observed_strategies[agent.strategy_key] = stats
                if agent.win_rate > best_wr:
                    best_wr = agent.win_rate
                    best_strategy = agent.strategy_key

        if best_strategy and best_strategy != self.active_strategy and best_wr > 55:
            old = self.active_strategy
            self.active_strategy = best_strategy
            self.strategy_key = best_strategy
            self.strategy = STRATEGIES[best_strategy]
            self.upgrade_count += 1
            msg = f"GURU UPGRADE #{self.upgrade_count}: Adopted {STRATEGIES[best_strategy]['name']} (WR={best_wr:.1f}%) from {old}"
            log.info(f"[TRADING GURU] 🧠 {msg}")
            self.knowledge_base["upgrades"].append({
                "time": datetime.now(timezone.utc).isoformat(),
                "from": old,
                "to": best_strategy,
                "reason": f"Peer WR={best_wr:.1f}%",
            })
            self._save_kb()
            return msg
        return None

    def record_pattern(self, asset, strategy, confirms, outcome):
        pattern = {
            "time": datetime.now(timezone.utc).isoformat(),
            "asset": asset,
            "strategy": strategy,
            "confirms": confirms,
            "outcome": outcome,
        }
        self.knowledge_base["patterns"].append(pattern)
        if len(self.knowledge_base["patterns"]) > 500:
            self.knowledge_base["patterns"] = self.knowledge_base["patterns"][-500:]
        self._save_kb()

# ─── MARKET DATA ─────────────────────────────────────────────────────────────

class MarketData:
    def __init__(self):
        self.exchange = ccxt.okx({"enableRateLimit": True})
        self.fallback = ccxt.kraken({"enableRateLimit": True})
        self.use_fallback = False
        self.price_history = {a: deque(maxlen=200) for a in ASSETS}
        self.high_history = {a: deque(maxlen=200) for a in ASSETS}
        self.low_history = {a: deque(maxlen=200) for a in ASSETS}
        self.volume_history = {a: deque(maxlen=200) for a in ASSETS}
        self.current_prices = {}

    async def fetch_prices(self):
        """Fetch individual tickers for each asset — works reliably on OKX and Kraken."""
        loop = asyncio.get_event_loop()
        fetched = 0
        for asset in ASSETS:
            try:
                if not self.use_fallback:
                    t = await loop.run_in_executor(None, lambda a=asset: self.exchange.fetch_ticker(a))
                else:
                    kraken_asset = ASSET_MAP_KRAKEN[asset]
                    t = await loop.run_in_executor(None, lambda a=kraken_asset: self.fallback.fetch_ticker(a))
                price = float(t["last"])
                high = float(t.get("high", price * 1.001))
                low = float(t.get("low", price * 0.999))
                vol = float(t.get("quoteVolume", 1000))
                self.current_prices[asset] = price
                self.price_history[asset].append(price)
                self.high_history[asset].append(high)
                self.low_history[asset].append(low)
                self.volume_history[asset].append(vol)
                fetched += 1
            except Exception as e:
                if not self.use_fallback:
                    log.warning(f"OKX error for {asset}, switching to Kraken: {str(e)[:80]}")
                    self.use_fallback = True
                else:
                    log.warning(f"Fetch error {asset}: {str(e)[:80]}")
        if fetched > 0:
            log.debug(f"Fetched {fetched}/{len(ASSETS)} assets | BTC={self.current_prices.get('BTC/USDT', 'N/A')}")
        return fetched > 0

    def get_history(self, asset):
        return (
            list(self.price_history[asset]),
            list(self.high_history[asset]),
            list(self.low_history[asset]),
            list(self.volume_history[asset]),
        )

# ─── PAPER TRADING ENGINE ────────────────────────────────────────────────────

class PaperTrader:
    def __init__(self):
        pass

    def open_short(self, agent, asset, price, confirms):
        if asset in agent.open_trades:
            return None  # already in trade
        if agent.halted_today:
            return None
        max_score = len(confirms) + 2
        sizing = gods_level_position(agent.capital, price, asset, len(confirms), max_score)
        trade = {
            "asset": asset,
            "entry_price": price,
            "stop_price": sizing["stop_price"],
            "tp_price": sizing["tp_price"],
            "position_usd": sizing["position_usd"],
            "units": sizing["units"],
            "risk_usd": sizing["risk_usd"],
            "confirms": confirms,
            "open_time": datetime.now(timezone.utc).isoformat(),
            "strategy": agent.strategy_key,
        }
        agent.open_trades[asset] = trade
        log.info(f"[{agent.name}] 📉 SHORT {asset} @ {price:.4f} | "
                 f"SL={sizing['stop_price']:.4f} TP={sizing['tp_price']:.4f} "
                 f"Size=${sizing['position_usd']:.2f} | {len(confirms)} confirms")
        return trade

    def check_exits(self, agent, market_data):
        closed = []
        for asset, trade in list(agent.open_trades.items()):
            price = market_data.current_prices.get(asset)
            if not price:
                continue
            hit_tp = price <= trade["tp_price"]
            hit_sl = price >= trade["stop_price"]
            if hit_tp or hit_sl:
                pnl_pct = (trade["entry_price"] - price) / trade["entry_price"]
                pnl_usd = pnl_pct * trade["position_usd"]
                agent.capital += pnl_usd
                agent.total_trades += 1
                if pnl_usd > 0:
                    agent.wins += 1
                    outcome = "WIN"
                else:
                    agent.losses += 1
                    agent.daily_loss += abs(pnl_usd)
                    outcome = "LOSS"
                    if agent.daily_loss >= agent.daily_loss_limit:
                        agent.halted_today = True
                        log.warning(f"[{agent.name}] ⛔ HALTED: Daily loss limit reached")
                agent.update_drawdown()
                agent.check_cold_wallet()
                result = {
                    "asset": asset,
                    "entry": trade["entry_price"],
                    "exit": price,
                    "pnl_usd": round(pnl_usd, 4),
                    "outcome": outcome,
                    "strategy": trade["strategy"],
                    "confirms": trade["confirms"],
                }
                agent.trade_log.append(result)
                if len(agent.trade_log) > 100:
                    agent.trade_log = agent.trade_log[-100:]
                del agent.open_trades[asset]
                closed.append(result)
                log.info(f"[{agent.name}] {'✅' if outcome=='WIN' else '❌'} {outcome} {asset} "
                         f"PnL=${pnl_usd:+.4f} | Capital=${agent.capital:.2f}")
        return closed

# ─── STATE PERSISTENCE ───────────────────────────────────────────────────────

def save_state(agents, guru, tick_count):
    state = {
        "tick": tick_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents": [a.to_dict() for a in agents],
        "guru": {**guru.to_dict(), "upgrade_count": guru.upgrade_count, "active_strategy": guru.active_strategy},
        "recent_trades": [],
    }
    for a in agents + [guru]:
        for t in a.trade_log[-5:]:
            state["recent_trades"].append({**t, "agent": a.name})
    state["recent_trades"].sort(key=lambda x: x.get("asset", ""), reverse=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log.warning(f"State save error: {e}")

# ─── MAIN ENGINE LOOP ────────────────────────────────────────────────────────

async def main():
    log.info("=" * 70)
    log.info("TRADING STRATEGIES TESTING ENGINE v2.0 — STARTING")
    log.info("8 Momentum Scalping Strategies | 8 Agents + Trading Guru Master")
    log.info(f"Assets: {', '.join(ASSETS)} | Mode: SHORT ONLY | Paper Trading")
    log.info("=" * 70)

    # Initialize agents — each specializes in one strategy
    strategy_keys = list(STRATEGIES.keys())
    agents = [
        TradingAgent("AGENT ALPHA",   "EMA_CROSS"),
        TradingAgent("AGENT BETA",    "VWAP_MACD"),
        TradingAgent("AGENT GAMMA",   "KELTNER_RSI"),
        TradingAgent("AGENT DELTA",   "BB_SQUEEZE"),
        TradingAgent("AGENT EPSILON", "SUPERTREND_MACD"),
        TradingAgent("AGENT ZETA",    "ORDER_FLOW"),
        TradingAgent("AGENT ETA",     "PIVOT_BREAKOUT"),
        TradingAgent("AGENT THETA",   "ALMA_STOCH"),
    ]
    guru = TradingGuru()
    market = MarketData()
    trader = PaperTrader()
    tick_count = 0
    last_daily_reset = datetime.now(timezone.utc).date()

    log.info(f"Initialized {len(agents)} specialist agents + Trading Guru master")
    for a in agents:
        log.info(f"  {a.name}: {a.strategy['name']} ({a.strategy['description'][:60]}...)")

    while True:
        try:
            tick_count += 1
            now = datetime.now(timezone.utc)

            # Daily reset of halt flags
            if now.date() != last_daily_reset:
                last_daily_reset = now.date()
                for a in agents + [guru]:
                    a.halted_today = False
                    a.daily_loss = 0.0
                log.info("📅 Daily reset: halt flags cleared, daily loss counters reset")

            # Fetch live market data
            success = await market.fetch_prices()
            if not success:
                await asyncio.sleep(TICK_INTERVAL)
                continue

            # Check exits for all agents
            for agent in agents + [guru]:
                closed = trader.check_exits(agent, market)
                for trade in closed:
                    guru.record_pattern(trade["asset"], trade["strategy"], trade["confirms"], trade["outcome"])

            # Evaluate entry signals for each agent on each asset
            for asset in ASSETS:
                prices, highs, lows, volumes = market.get_history(asset)
                if len(prices) < MIN_HISTORY:
                    continue
                price = market.current_prices.get(asset)
                if not price:
                    continue

                # Each specialist agent evaluates its own strategy
                for agent in agents:
                    if agent.halted_today or asset in agent.open_trades:
                        continue
                    signal_fn = STRATEGY_SIGNALS[agent.strategy_key]
                    score, confirms = signal_fn(prices, highs, lows, volumes)
                    min_confirm = STRATEGIES[agent.strategy_key]["min_confirm"]
                    if score >= min_confirm:
                        trader.open_short(agent, asset, price, confirms)

                # Trading Guru uses its currently active (best-learned) strategy
                if not guru.halted_today and asset not in guru.open_trades:
                    signal_fn = STRATEGY_SIGNALS[guru.active_strategy]
                    score, confirms = signal_fn(prices, highs, lows, volumes)
                    min_confirm = STRATEGIES[guru.active_strategy]["min_confirm"]
                    if score >= min_confirm:
                        trader.open_short(guru, asset, price, confirms)

            # Guru observes and learns from peers every 10 ticks
            if tick_count % 10 == 0:
                upgrade_msg = guru.observe_agents(agents)
                if upgrade_msg:
                    log.info(f"[GURU SELF-LEARNING] {upgrade_msg}")

            # Save state every 5 ticks
            if tick_count % 5 == 0:
                save_state(agents, guru, tick_count)

            # Log leaderboard every 20 ticks
            if tick_count % 20 == 0:
                log.info("─" * 70)
                log.info(f"LEADERBOARD (Tick #{tick_count})")
                all_agents = sorted(agents + [guru], key=lambda a: a.total_value, reverse=True)
                for rank, a in enumerate(all_agents, 1):
                    log.info(f"  #{rank} {a.name:<20} Cap=${a.capital:>8.2f} "
                             f"Cold=${a.cold_wallet:>7.2f} WR={a.win_rate:>5.1f}% "
                             f"({a.wins}W/{a.losses}L) [{a.strategy['name'][:25]}]")
                log.info("─" * 70)

            await asyncio.sleep(TICK_INTERVAL)

        except KeyboardInterrupt:
            log.info("Engine stopped by user.")
            save_state(agents, guru, tick_count)
            break
        except Exception as e:
            log.error(f"Engine error (tick {tick_count}): {e}", exc_info=True)
            await asyncio.sleep(TICK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
