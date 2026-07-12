import time
import random
import os
from trading_guru.core.config import config
from trading_guru.core.models import EngineState, MarketData, TradeSignal, ActiveTrade
from trading_guru.utils.market_utils import get_live_market_data
from trading_guru.agents.llm_agent import ALL_AGENTS, get_ai_consensus
from trading_guru.core.alpha_arena import alpha_validator, smart_gate

class TradingEngine:
    def __init__(self, pair: str, budget: float):
        self.state = EngineState(
            pair=pair,
            budget=budget,
            peak_budget=budget,
            dynamic_risk_percent=config.BASE_RISK_PER_TRADE_PERCENT
        )
        print(f"🛡️ UNBREAKABLE Engine for {self.state.pair} activated with budget ${self.state.budget:,.2f}")

    def run_cycle(self):
        try:
            market_data = get_live_market_data(self.state.pair)
            
            if not self._run_circuit_breakers(market_data):
                return
            
            if self.state.active_trade:
                self._manage_active_trade(market_data)
            else:
                self._find_new_trade(market_data)
                
        except Exception as e:
            print(f"❌ ERROR in {self.state.pair} engine: {e}")
            self.state.status = "ERROR"

    def _run_circuit_breakers(self, market_data: MarketData) -> bool:
        if self.state.consecutive_losses >= config.CONSECUTIVE_LOSS_LIMIT:
            self.state.status = f"PAUSED ({config.CONSECUTIVE_LOSS_LIMIT} Losses)"
            print(f"🛑 CIRCUIT BREAKER [{self.state.pair}]: Paused due to {config.CONSECUTIVE_LOSS_LIMIT} consecutive losses.")
            time.sleep(5)
            self.state.consecutive_losses = 0
            self.state.status = "ACTIVE"
            return False
        
        drawdown = 0
        if self.state.peak_budget > 0:
            drawdown = (self.state.budget - self.state.peak_budget) / self.state.peak_budget * 100
        
        if drawdown < config.PEAK_DRAWDOWN_LIMIT_PERCENT:
            self.state.dynamic_risk_percent = config.BASE_RISK_PER_TRADE_PERCENT / 2
            print(f"🛑 CIRCUIT BREAKER [{self.state.pair}]: Drawdown > {abs(config.PEAK_DRAWDOWN_LIMIT_PERCENT)}%. Risk reduced.")
        else:
            self.state.dynamic_risk_percent = config.BASE_RISK_PER_TRADE_PERCENT
        
        volatility_threshold = market_data.price * 0.05 * config.VOLATILITY_SPIKE_MULTIPLE
        if market_data.volatility_atr > volatility_threshold:
            self.state.status = "PAUSED (Volatility)"
            print(f"🛑 CIRCUIT BREAKER [{self.state.pair}]: Paused due to extreme volatility.")
            time.sleep(3)
            self.state.status = "ACTIVE"
            return False
        
        return True

    def _select_dynamic_strategy(self, market_data: MarketData):
        if market_data.adx_14 > config.TREND_ADX_THRESHOLD:
            self.state.current_strategy = "waterfall"
        elif market_data.adx_14 < config.RANGE_ADX_THRESHOLD:
            self.state.current_strategy = "scalping"
        else:
            self.state.current_strategy = "pyramid"
        
        if self.state.consecutive_losses >= 2:
            self.state.current_strategy = "doubling"

    def _find_new_trade(self, market_data: MarketData):
        self._select_dynamic_strategy(market_data)
        
        stats = self.state.strategy_stats[self.state.current_strategy]
        if not stats.is_active:
            return
        
        consensus = get_ai_consensus(market_data)
        if consensus != "short":
            return
        
        gate_passed, gate_status = smart_gate.check_all_gates(
            market_data, 
            ai_votes=5,
            budget=self.state.budget,
            active_positions=1 if self.state.active_trade else 0
        )
        
        if not gate_passed:
            failed_gates = [k for k, v in gate_status.items() if not v]
            return
        
        agent = ALL_AGENTS[0]
        signal = agent.analyze(
            market_data,
            self.state.current_strategy,
            self.state.budget,
            self.state.dynamic_risk_percent
        )
        
        arena_passed, failed_pillars = alpha_validator.validate_trade(
            signal, market_data, self.state.budget
        )
        
        if not arena_passed:
            print(f"⛔ [{self.state.pair}] Alpha Arena REJECTED: {failed_pillars[0]}")
            return
        
        self._enter_trade(signal)

    def _enter_trade(self, signal: TradeSignal):
        self.state.active_trade = ActiveTrade(
            signal=signal,
            current_stop_loss=signal.stop_loss,
            remaining_position_size_usd=signal.initial_position_size_usd
        )
        self.state.trade_count += 1
        
        print(f"🎯 [{self.state.pair}] #{self.state.trade_count} {signal.strategy.upper()} SHORT @ ${signal.entry_price:,.4f} | SL: ${signal.stop_loss:,.4f} | Size: ${signal.initial_position_size_usd:,.2f}")

    def _manage_active_trade(self, market_data: MarketData):
        trade = self.state.active_trade
        price = market_data.price
        entry = trade.signal.entry_price
        risk_distance = abs(trade.signal.stop_loss - entry)
        profit_r = (entry - price) / risk_distance if risk_distance != 0 else 0
        
        if price >= trade.current_stop_loss:
            self._close_trade(price, "SL HIT")
            return
        
        if price <= trade.signal.tp3:
            self._close_trade(price, "TP3 HIT")
            return
        
        if price <= trade.signal.tp2 and not trade.tp2_hit:
            close_pct = 0.50 / (trade.remaining_position_size_usd / trade.signal.initial_position_size_usd)
            self._take_profit(price, min(close_pct, 0.667), "TP2 (50%)")
            trade.tp2_hit = True
            return
        
        if price <= trade.signal.tp1 and not trade.tp1_hit:
            self._take_profit(price, 0.25, "TP1 (25%)")
            trade.tp1_hit = True
            if not trade.breakeven_set:
                self._move_stop_to_breakeven()
            return
        
        if profit_r >= config.BREAKEVEN_TRIGGER_R and not trade.breakeven_set:
            self._move_stop_to_breakeven()
        
        if trade.tp1_hit and not trade.trailing_activated:
            new_sl = price + (market_data.volatility_atr * config.TRAILING_STOP_ATR_MULTIPLE)
            if new_sl < trade.current_stop_loss:
                trade.current_stop_loss = new_sl
                trade.trailing_activated = True
                print(f"📈 [{self.state.pair}] Trailing stop @ ${new_sl:,.4f}")
        elif trade.trailing_activated:
            new_sl = price + (market_data.volatility_atr * config.TRAILING_STOP_ATR_MULTIPLE)
            if new_sl < trade.current_stop_loss:
                trade.current_stop_loss = new_sl

    def _take_profit(self, exit_price: float, percentage: float, label: str):
        trade = self.state.active_trade
        size_to_close = trade.remaining_position_size_usd * percentage
        
        pnl = (trade.signal.entry_price - exit_price) / trade.signal.entry_price * size_to_close
        self.state.pnl += pnl
        self.state.budget += pnl
        self.state.peak_budget = max(self.state.peak_budget, self.state.budget)
        
        trade.remaining_position_size_usd -= size_to_close
        
        print(f"💰 [{self.state.pair}] {label} +${pnl:.2f} | Remaining: ${trade.remaining_position_size_usd:.2f}")

    def _move_stop_to_breakeven(self):
        trade = self.state.active_trade
        trade.current_stop_loss = trade.signal.entry_price
        trade.breakeven_set = True
        print(f"🛡️ [{self.state.pair}] Stop moved to BREAKEVEN @ ${trade.signal.entry_price:,.4f}")

    def _close_trade(self, exit_price: float, reason: str):
        trade = self.state.active_trade
        
        pnl = (trade.signal.entry_price - exit_price) / trade.signal.entry_price * trade.remaining_position_size_usd
        self.state.pnl += pnl
        self.state.budget += pnl
        self.state.peak_budget = max(self.state.peak_budget, self.state.budget)
        
        is_win = pnl > 0
        if is_win:
            self.state.consecutive_losses = 0
            icon = "💰"
        else:
            self.state.consecutive_losses += 1
            icon = "🔴"
        
        self._update_strategy_performance(trade.signal.strategy, is_win)
        self._adjust_risk_kelly(is_win)
        self._log_trade(exit_price, reason, pnl)
        
        wr = self._get_win_rate()
        print(f"{icon} [{self.state.pair}] #{self.state.trade_count} {reason} | Exit: ${exit_price:,.4f} | PNL: ${pnl:+.2f} | Engine PNL: ${self.state.pnl:+.2f} | WR: {wr:.0f}%")
        
        self.state.active_trade = None

    def _update_strategy_performance(self, strategy: str, is_win: bool):
        stats = self.state.strategy_stats[strategy]
        if is_win:
            stats.wins += 1
        else:
            stats.losses += 1
        
        total = stats.wins + stats.losses
        stats.win_rate = (stats.wins / total) if total > 0 else 0
        
        if stats.win_rate < config.STRATEGY_PERFORMANCE_THRESHOLD and total > 10:
            stats.is_active = False
            print(f"🔧 SELF-HEALING [{self.state.pair}]: {strategy} DISABLED (WR: {stats.win_rate:.0%})")

    def _adjust_risk_kelly(self, is_win: bool):
        if is_win:
            self.state.dynamic_risk_percent = min(
                self.state.dynamic_risk_percent * (1 + config.KELLY_FRACTION),
                5.0
            )
        else:
            self.state.dynamic_risk_percent = max(
                self.state.dynamic_risk_percent * (1 - config.KELLY_FRACTION),
                0.5
            )
        print(f"🔧 DYNAMIC RISK [{self.state.pair}]: Adjusted to {self.state.dynamic_risk_percent:.2f}%")

    def _get_win_rate(self) -> float:
        total_wins = sum(s.wins for s in self.state.strategy_stats.values())
        total_losses = sum(s.losses for s in self.state.strategy_stats.values())
        total = total_wins + total_losses
        return (total_wins / total * 100) if total > 0 else 0

    def _log_trade(self, exit_price: float, reason: str, pnl: float):
        try:
            os.makedirs("logs", exist_ok=True)
            filename = f"logs/{self.state.pair.replace('/', '_')}_trades.log"
            with open(filename, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{self.state.active_trade.signal.strategy},{reason},{self.state.active_trade.signal.entry_price},{exit_price},{pnl:.2f}\n")
        except:
            pass
