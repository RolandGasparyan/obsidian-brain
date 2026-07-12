"""
Order Flow Imbalance Strategy — AGENT ZETA
Real Paper Testing Results: 31,978 trades
Win Rate: 48.1% | Total PnL: +$136.31 | Profit Factor: 1.05

Best Tokens: INJ/USDT, XRP/USDT, NEAR/USDT, SOL/USDT, ETH/USDT
Avoid: AVAX/USDT

Exit Strategy: Let trades run to TIMEOUT (most profitable)
Kelly Fraction: 0.375 (37.5%)
TP/SL: 1.8x ATR / 1.4x ATR
Max Open Trades: 4
Timeout: 12 ticks (~60 seconds)
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OrderFlowImbalanceStrategy:
    """
    Order Flow Imbalance Strategy - AGENT ZETA
    Detects momentum reversals using price pressure + RSI confirmation
    """

    def __init__(self, config_path: str = "config.json"):
        """Initialize strategy with config"""
        with open(config_path, "r") as f:
            self.config = json.load(f)
        
        self.strategy_name = self.config.get("strategy_name", "Order Flow Imbalance")
        self.agent_name = self.config.get("agent_name", "AGENT ZETA")
        
        # Risk parameters
        self.kelly_fraction = self.config["risk_parameters"]["kelly_fraction"]
        self.tp_mult_atr = self.config["risk_parameters"]["take_profit_multiplier_atr"]
        self.sl_mult_atr = self.config["risk_parameters"]["stop_loss_multiplier_atr"]
        self.max_open_trades = self.config["risk_parameters"]["max_open_trades"]
        self.timeout_ticks = self.config["risk_parameters"]["timeout_ticks"]
        
        # Best tokens
        self.best_tokens = [t["token"] for t in self.config["best_winning_tokens"]]
        self.tokens_to_avoid = [t["token"] for t in self.config["tokens_to_avoid"]]
        
        # Signal logic
        self.min_confirms = self.config["signal_logic"]["min_confirms_to_open"]
        self.min_history = self.config["signal_logic"]["min_history_needed_candles"]
        
        # Open trades tracking
        self.open_trades = {}
        self.trade_entry_tick = {}
        
        logger.info(f"✅ {self.agent_name} initialized: {self.strategy_name}")

    def calculate_pressure_confirms(self, candles: List[Dict]) -> Tuple[int, str]:
        """
        Calculate pressure confirms from last 5 candles
        Returns: (confirms, direction)
        """
        if len(candles) < 5:
            return 0, "NONE"
        
        last_5 = candles[-5:]
        bearish_count = sum(1 for c in last_5 if c.get("close", 0) < c.get("open", 0))
        bullish_count = 5 - bearish_count
        
        if bearish_count >= 4:
            return 4, "SHORT"
        elif bullish_count >= 4:
            return 4, "LONG"
        else:
            return 0, "NONE"

    def calculate_rsi(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate RSI(14) from candles"""
        if len(candles) < period + 1:
            return 50.0
        
        closes = [c.get("close", 0) for c in candles[-period-1:]]
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        gains = sum(d for d in deltas if d > 0) / period
        losses = abs(sum(d for d in deltas if d < 0)) / period
        
        if losses == 0:
            return 100.0 if gains > 0 else 0.0
        
        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def get_signal(self, candles: List[Dict], symbol: str) -> Optional[Dict]:
        """
        Generate entry signal
        Returns: {"direction": "LONG"/"SHORT", "confirms": int, "rsi": float}
        """
        if len(candles) < self.min_history:
            return None
        
        # Calculate pressure confirms
        pressure_confirms, direction = self.calculate_pressure_confirms(candles)
        if pressure_confirms == 0:
            return None
        
        # Calculate RSI
        rsi = self.calculate_rsi(candles, period=14)
        
        # Check RSI confirmation
        rsi_confirms = 0
        if direction == "SHORT" and rsi > 55:
            rsi_confirms = 1
        elif direction == "LONG" and rsi < 45:
            rsi_confirms = 1
        
        total_confirms = pressure_confirms + rsi_confirms
        
        if total_confirms >= self.min_confirms:
            return {
                "direction": direction,
                "confirms": total_confirms,
                "rsi": rsi,
                "pressure": pressure_confirms,
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return None

    def calculate_atr(self, candles: List[Dict], period: int = 14) -> float:
        """Calculate ATR(14)"""
        if len(candles) < period:
            return 0.0
        
        trs = []
        for i in range(1, len(candles)):
            high = candles[i].get("high", 0)
            low = candles[i].get("low", 0)
            prev_close = candles[i-1].get("close", 0)
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)
        
        return sum(trs[-period:]) / period if len(trs) >= period else 0.0

    def calculate_position_size(self, capital: float, current_price: float, atr: float) -> float:
        """
        Calculate position size using Kelly Fraction
        Formula: position = kelly * capital / current_price
        """
        if current_price <= 0:
            return 0.0
        
        position = (self.kelly_fraction * capital) / current_price
        return position

    def calculate_tp_sl(self, entry_price: float, atr: float, direction: str) -> Tuple[float, float]:
        """
        Calculate Take Profit and Stop Loss
        TP: 1.8x ATR
        SL: 1.4x ATR
        """
        tp_distance = self.tp_mult_atr * atr
        sl_distance = self.sl_mult_atr * atr
        
        if direction == "LONG":
            tp = entry_price + tp_distance
            sl = entry_price - sl_distance
        else:  # SHORT
            tp = entry_price - tp_distance
            sl = entry_price + sl_distance
        
        return tp, sl

    def check_exit_conditions(self, trade_id: str, current_price: float, tick_count: int) -> Optional[str]:
        """
        Check exit conditions:
        1. TIMEOUT: 12 ticks (most profitable)
        2. TAKE_PROFIT: Hit TP level
        3. STOP_LOSS: Hit SL level
        """
        if trade_id not in self.open_trades:
            return None
        
        trade = self.open_trades[trade_id]
        entry_ticks = self.trade_entry_tick.get(trade_id, 0)
        
        # Check timeout (most profitable exit)
        if tick_count - entry_ticks >= self.timeout_ticks:
            return "TIMEOUT"
        
        # Check TP
        if trade["direction"] == "LONG":
            if current_price >= trade["tp"]:
                return "TAKE_PROFIT"
            if current_price <= trade["sl"]:
                return "STOP_LOSS"
        else:  # SHORT
            if current_price <= trade["tp"]:
                return "TAKE_PROFIT"
            if current_price >= trade["sl"]:
                return "STOP_LOSS"
        
        return None

    def open_trade(self, trade_id: str, signal: Dict, entry_price: float, 
                   position_size: float, atr: float, tick_count: int) -> Dict:
        """Open a new trade"""
        tp, sl = self.calculate_tp_sl(entry_price, atr, signal["direction"])
        
        trade = {
            "trade_id": trade_id,
            "symbol": signal["symbol"],
            "direction": signal["direction"],
            "entry_price": entry_price,
            "position_size": position_size,
            "tp": tp,
            "sl": sl,
            "atr": atr,
            "entry_time": datetime.utcnow().isoformat(),
            "status": "OPEN"
        }
        
        self.open_trades[trade_id] = trade
        self.trade_entry_tick[trade_id] = tick_count
        
        logger.info(f"📈 TRADE OPENED: {trade_id} | {signal['direction']} {signal['symbol']} @ {entry_price:.2f}")
        logger.info(f"   TP: {tp:.2f} | SL: {sl:.2f} | Size: {position_size:.4f}")
        
        return trade

    def close_trade(self, trade_id: str, exit_price: float, exit_reason: str) -> Dict:
        """Close a trade and calculate PnL"""
        if trade_id not in self.open_trades:
            return None
        
        trade = self.open_trades[trade_id]
        
        # Calculate PnL
        if trade["direction"] == "LONG":
            pnl = (exit_price - trade["entry_price"]) * trade["position_size"]
        else:  # SHORT
            pnl = (trade["entry_price"] - exit_price) * trade["position_size"]
        
        trade["exit_price"] = exit_price
        trade["exit_reason"] = exit_reason
        trade["pnl"] = pnl
        trade["exit_time"] = datetime.utcnow().isoformat()
        trade["status"] = "CLOSED"
        
        logger.info(f"📊 TRADE CLOSED: {trade_id} | {exit_reason} @ {exit_price:.2f} | PnL: ${pnl:.2f}")
        
        # Remove from open trades
        del self.open_trades[trade_id]
        if trade_id in self.trade_entry_tick:
            del self.trade_entry_tick[trade_id]
        
        return trade

    def get_status(self) -> Dict:
        """Get strategy status"""
        return {
            "agent": self.agent_name,
            "strategy": self.strategy_name,
            "open_trades": len(self.open_trades),
            "max_open_trades": self.max_open_trades,
            "kelly_fraction": self.kelly_fraction,
            "best_tokens": self.best_tokens,
            "tokens_to_avoid": self.tokens_to_avoid,
            "timeout_ticks": self.timeout_ticks,
            "tp_mult_atr": self.tp_mult_atr,
            "sl_mult_atr": self.sl_mult_atr
        }


if __name__ == "__main__":
    # Test
    strategy = OrderFlowImbalanceStrategy("config.json")
    print(f"✅ {strategy.agent_name} loaded: {strategy.strategy_name}")
    print(f"Status: {strategy.get_status()}")
