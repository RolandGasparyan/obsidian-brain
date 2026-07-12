"""
Trading Guru Bot - ADVANCED STRATEGY SYSTEM
Dynamic Multi-Strategy with AI Model Signals

STRATEGIES:
- SCALPING: Ultra-fast micro-profits in ranging markets (ADX < 20)
- WATERFALL: 3-entry cascade with decreasing size for trending markets (ADX 25-40)
- SNOWBALL: Compound funding rate profits during high funding periods
- PYRAMID: Max aggression in hyper-trending markets with increasing layers (ADX > 40)

SAFE VERSION with:
- 3x leverage (instead of 5x)
- 1% position size (instead of 2%)
- 2% daily loss limit (instead of 5%)
- Mandatory Stop Loss on all trades
- SHORTS ONLY with 6-Agent AI Consensus
"""

import gate_api
from gate_api.exceptions import GateApiException
import time
import logging
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SafeTradingGuru')


class Strategy(Enum):
    SCALPING = "SCALPING"
    WATERFALL = "WATERFALL"
    SNOWBALL = "SNOWBALL"
    PYRAMID = "PYRAMID"


class SafeConfig:
    """SAFE configuration - Balance Protection with Multi-Strategy"""
    
    API_KEY = os.environ.get('GATE_API_KEY', '')
    API_SECRET = os.environ.get('GATE_API_SECRET', '')
    HOST = "https://api.gateio.ws/api/v4"
    SETTLE = "usdt"
    
    TRADING_PAIRS = [
        "BTC_USDT", "SOL_USDT", "ETH_USDT", "XRP_USDT", "AVAX_USDT"
    ]
    
    MAKER_FEE = 0.0009
    TAKER_FEE = 0.0009
    
    TOTAL_BALANCE = 400.0
    
    MAX_LEVERAGE = 3
    MAX_POSITION_SIZE_PCT = 0.01
    DAILY_LOSS_LIMIT_PCT = 0.02
    
    SCALP_TARGET_PCT = 0.012
    SCALP_STOP_LOSS_PCT = 0.015
    SCALP_MAX_TRADES = 20
    
    ENABLE_MARTINGALE = False
    ENABLE_GRID = False
    STOP_LOSS_MANDATORY = True
    
    LOOP_DELAY_SEC = 2
    TRADE_COOLDOWN_SEC = 30
    PAIR_SCAN_INTERVAL = 60
    
    MIN_AI_VOTES = 4
    MIN_SCORE = 75
    
    MIN_FUNDING_RATE = 0.0001
    MIN_VOLUME_24H = 1000000
    MIN_VOLATILITY = 0.01
    
    ADX_HYPER_TREND = 40
    ADX_TREND = 25
    ADX_RANGE = 20
    
    WATERFALL_ENTRIES = 3
    WATERFALL_SIZES = [1.0, 0.5, 0.3]
    WATERFALL_SPACING_PCT = 0.003
    WATERFALL_TP_PCT = 0.018
    WATERFALL_SL_PCT = 0.020
    
    SNOWBALL_MIN_FUNDING = 0.0005
    SNOWBALL_HOLD_HOURS = 8
    SNOWBALL_TP_PCT = 0.015
    SNOWBALL_SL_PCT = 0.015
    
    PYRAMID_ENTRIES = 3
    PYRAMID_MULTIPLIER = 1.5
    PYRAMID_SPACING_PCT = 0.004
    PYRAMID_TP_PCT = 0.025
    PYRAMID_SL_PCT = 0.025


class GateClient:
    def __init__(self, config):
        self.config = config
        self.api = gate_api.FuturesApi(
            gate_api.ApiClient(
                gate_api.Configuration(
                    key=config.API_KEY,
                    secret=config.API_SECRET,
                    host=config.HOST
                )
            )
        )
    
    def get_all_tickers(self):
        try:
            return self.api.list_futures_tickers(self.config.SETTLE)
        except:
            return []
    
    def get_ticker(self, contract):
        try:
            t = self.api.list_futures_tickers(self.config.SETTLE, contract=contract)
            return t[0] if t else None
        except:
            return None
    
    def get_contract_info(self, contract):
        try:
            return self.api.get_futures_contract(self.config.SETTLE, contract)
        except:
            return None
    
    def get_price(self, contract="BTC_USDT"):
        try:
            t = self.api.list_futures_tickers(self.config.SETTLE, contract=contract)
            return float(t[0].last) if t else None
        except:
            return None
    
    def get_funding(self, contract="BTC_USDT"):
        try:
            t = self.api.list_futures_tickers(self.config.SETTLE, contract=contract)
            return float(t[0].funding_rate or 0) if t else 0
        except:
            return 0
    
    def get_balance(self):
        try:
            a = self.api.list_futures_accounts(self.config.SETTLE)
            return float(a.available)
        except:
            return 0
    
    def get_account(self):
        try:
            return self.api.list_futures_accounts(self.config.SETTLE)
        except:
            return None
    
    def get_positions(self):
        try:
            return self.api.list_positions(self.config.SETTLE)
        except:
            return []
    
    def set_leverage(self, contract, leverage):
        """Set leverage for a contract before trading (isolated margin mode)"""
        try:
            self.api.update_position_leverage(
                self.config.SETTLE,
                contract,
                str(leverage)
            )
            logger.info(f"Leverage set: {contract} -> {leverage}x")
            return True
        except Exception as e:
            if "position exists" in str(e).lower():
                logger.debug(f"Position exists, leverage unchanged: {contract}")
            else:
                logger.warning(f"Leverage update {contract}: {e}")
            return False
    
    def place_short(self, contract, size):
        try:
            self.set_leverage(contract, self.config.MAX_LEVERAGE)
            
            order = gate_api.FuturesOrder(
                contract=contract,
                size=-abs(size),
                price="0",
                tif="ioc"
            )
            return self.api.create_futures_order(self.config.SETTLE, order)
        except Exception as e:
            logger.error(f"Order error {contract}: {e}")
            return None
    
    def close_position(self, contract, size):
        try:
            order = gate_api.FuturesOrder(
                contract=contract,
                size=-size,
                price="0",
                tif="ioc"
            )
            return self.api.create_futures_order(self.config.SETTLE, order)
        except:
            return None


class PairScanner:
    """Scans and ranks trading pairs for profitability with ADX estimation"""
    
    def __init__(self, config, client):
        self.config = config
        self.client = client
        self.pair_scores = {}
        self.last_scan = 0
        self.best_pairs = []
    
    def estimate_adx(self, volatility, change_24h):
        """Estimate ADX from volatility and price change"""
        abs_change = abs(change_24h)
        if abs_change > 5 and volatility > 0.06:
            return 45
        elif abs_change > 3 and volatility > 0.04:
            return 35
        elif abs_change > 2 and volatility > 0.02:
            return 28
        elif abs_change > 1:
            return 22
        else:
            return 15
    
    def scan_pair(self, contract):
        try:
            ticker = self.client.get_ticker(contract)
            if not ticker:
                return None
            
            price = float(ticker.last or 0)
            funding = float(ticker.funding_rate or 0)
            volume = float(ticker.volume_24h_base or 0) * price
            change = float(ticker.change_percentage or 0)
            high = float(ticker.high_24h or price)
            low = float(ticker.low_24h or price)
            
            if price <= 0 or volume < self.config.MIN_VOLUME_24H:
                return None
            
            volatility = (high - low) / price if price > 0 else 0
            adx = self.estimate_adx(volatility, change)
            
            score = 0
            reasons = []
            
            if funding > 0.0001:
                score += 30
                reasons.append(f"High Funding +{funding*100:.3f}%")
            elif funding > 0:
                score += 15
                reasons.append(f"Positive Funding +{funding*100:.4f}%")
            
            if change > 3:
                score += 25
                reasons.append(f"Pumped +{change:.1f}% (reversal)")
            elif change > 1:
                score += 15
                reasons.append(f"Up +{change:.1f}%")
            elif change < -3:
                score -= 10
                reasons.append(f"Dumping {change:.1f}%")
            
            if volatility > 0.05:
                score += 20
                reasons.append(f"High Vol {volatility*100:.1f}%")
            elif volatility > 0.02:
                score += 10
                reasons.append(f"Good Vol {volatility*100:.1f}%")
            
            if volume > 50000000:
                score += 15
                reasons.append("Very High Liquidity")
            elif volume > 10000000:
                score += 10
                reasons.append("Good Liquidity")
            
            return {
                "contract": contract,
                "price": price,
                "funding": funding,
                "change_24h": change,
                "volatility": volatility,
                "volume_24h": volume,
                "adx": adx,
                "score": max(0, score),
                "reasons": reasons
            }
        except:
            return None
    
    def scan_all(self):
        results = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.scan_pair, pair): pair 
                      for pair in self.config.TRADING_PAIRS}
            
            for future in as_completed(futures):
                result = future.result()
                if result and result["score"] > 0:
                    results.append(result)
        
        results.sort(key=lambda x: x["score"], reverse=True)
        
        self.pair_scores = {r["contract"]: r for r in results}
        self.best_pairs = results[:5]
        self.last_scan = time.time()
        
        return results
    
    def get_best_pairs(self, top_n=3):
        if time.time() - self.last_scan > self.config.PAIR_SCAN_INTERVAL:
            self.scan_all()
        
        return self.best_pairs[:top_n]
    
    def display_rankings(self):
        if not self.best_pairs:
            self.scan_all()
        
        print("\n" + "=" * 70)
        print("TOP PROFITABLE PAIRS FOR SHORTS (MULTI-STRATEGY MODE)")
        print("=" * 70)
        
        for i, pair in enumerate(self.best_pairs, 1):
            print(f"\n#{i} {pair['contract']} - Score: {pair['score']} | ADX: {pair['adx']}")
            print(f"   Price: ${pair['price']:,.4f} | Change: {pair['change_24h']:+.2f}%")
            print(f"   Funding: {pair['funding']*100:+.4f}% | Volatility: {pair['volatility']*100:.2f}%")
            print(f"   Volume: ${pair['volume_24h']/1e6:.1f}M")
            print(f"   Reasons: {', '.join(pair['reasons'])}")
        
        print("=" * 70 + "\n")


class AIEngine:
    """Enhanced AI Engine with Strategy Recommendations"""
    
    def __init__(self):
        try:
            from trading_guru.agents.llm_agent import get_multi_agent_consensus
            from trading_guru.core.models import MarketData
            self.consensus = get_multi_agent_consensus
            self.MarketData = MarketData
            self.ok = True
            logger.info("AI Engine: 6 agents ready (Multi-Strategy Mode)")
        except Exception as e:
            logger.warning(f"AI disabled: {e}")
            self.ok = False
    
    def analyze(self, contract, price, funding=0, volatility=0.015, adx=25, strategy=Strategy.SCALPING):
        if not self.ok:
            return {"votes": 0, "score": 0, "go": False, "strategy": Strategy.SCALPING, "confidence": 0}
        
        try:
            symbol = contract.replace("_", "/")
            
            strategy_prompt = f"""
STRATEGY: {strategy.value}
ADX: {adx} | Funding: {funding*100:.4f}%

Analyze for {strategy.value} strategy:
- SCALPING: Quick 0.3-0.8% targets, ADX < 20 (ranging)
- WATERFALL: 3-layer entries, ADX 25-40 (trending)
- SNOWBALL: Hold for funding collection, high funding > 0.05%
- PYRAMID: Aggressive 3-layer increasing size, ADX > 40 (hyper-trend)

Provide SHORT signal confidence for {symbol}
"""
            
            data = self.MarketData(
                symbol=symbol,
                price=price,
                volume_24h=1e9,
                volatility_atr=price * volatility,
                adx_14=adx,
                spread_percent=0.001,
                funding_rate=funding * 100,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            r = self.consensus(data, strategy_prompt)
            
            min_votes = 4 if strategy in [Strategy.SCALPING, Strategy.SNOWBALL] else 5
            min_score = 75 if strategy == Strategy.SCALPING else 80
            
            go = r["consensus"] == "short" and r["short_votes"] >= min_votes and r["avg_score"] >= min_score
            
            return {
                "votes": r["short_votes"],
                "score": r["avg_score"],
                "go": go,
                "strategy": strategy,
                "confidence": r["avg_score"] / 100,
                "agents": r.get("agents", [])
            }
        except Exception as e:
            logger.error(f"AI error: {e}")
            return {"votes": 0, "score": 0, "go": False, "strategy": Strategy.SCALPING, "confidence": 0}


class StrategyEngine:
    """Dynamic Strategy Selection Engine based on Market Conditions"""
    
    def __init__(self, config):
        self.config = config
        self.current_strategy = Strategy.SCALPING
        self.strategy_stats = {
            Strategy.SCALPING: {"wins": 0, "losses": 0},
            Strategy.WATERFALL: {"wins": 0, "losses": 0},
            Strategy.SNOWBALL: {"wins": 0, "losses": 0},
            Strategy.PYRAMID: {"wins": 0, "losses": 0}
        }
        self.active_layers = {}
    
    def select_strategy(self, adx, funding, volatility):
        """Select optimal strategy based on market conditions"""
        
        if funding > self.config.SNOWBALL_MIN_FUNDING:
            selected = Strategy.SNOWBALL
            reason = f"High Funding {funding*100:.3f}%"
        elif adx >= self.config.ADX_HYPER_TREND:
            selected = Strategy.PYRAMID
            reason = f"Hyper-Trend ADX={adx}"
        elif adx >= self.config.ADX_TREND:
            selected = Strategy.WATERFALL
            reason = f"Trending ADX={adx}"
        else:
            selected = Strategy.SCALPING
            reason = f"Ranging ADX={adx}"
        
        if selected != self.current_strategy:
            logger.info(f"Strategy Switch: {self.current_strategy.value} -> {selected.value} ({reason})")
            self.current_strategy = selected
        
        return selected, reason
    
    def get_entry_params(self, strategy, base_size, price):
        """Get entry parameters for each strategy"""
        
        if strategy == Strategy.SCALPING:
            return [{
                "size": base_size,
                "entry_offset": 0,
                "tp_pct": self.config.SCALP_TARGET_PCT,
                "sl_pct": self.config.SCALP_STOP_LOSS_PCT
            }]
        
        elif strategy == Strategy.WATERFALL:
            entries = []
            for i, size_mult in enumerate(self.config.WATERFALL_SIZES):
                entries.append({
                    "size": max(1, int(base_size * size_mult)),
                    "entry_offset": i * self.config.WATERFALL_SPACING_PCT,
                    "tp_pct": self.config.WATERFALL_TP_PCT,
                    "sl_pct": self.config.WATERFALL_SL_PCT,
                    "layer": i + 1
                })
            return entries
        
        elif strategy == Strategy.SNOWBALL:
            return [{
                "size": base_size,
                "entry_offset": 0,
                "tp_pct": self.config.SNOWBALL_TP_PCT,
                "sl_pct": self.config.SNOWBALL_SL_PCT,
                "hold_hours": self.config.SNOWBALL_HOLD_HOURS
            }]
        
        elif strategy == Strategy.PYRAMID:
            entries = []
            current_size = base_size
            for i in range(self.config.PYRAMID_ENTRIES):
                entries.append({
                    "size": max(1, int(current_size)),
                    "entry_offset": i * self.config.PYRAMID_SPACING_PCT,
                    "tp_pct": self.config.PYRAMID_TP_PCT,
                    "sl_pct": self.config.PYRAMID_SL_PCT,
                    "layer": i + 1
                })
                current_size *= self.config.PYRAMID_MULTIPLIER
            return entries
        
        return [{"size": base_size, "entry_offset": 0, "tp_pct": 0.008, "sl_pct": 0.004}]
    
    def record_result(self, strategy, won):
        if won:
            self.strategy_stats[strategy]["wins"] += 1
        else:
            self.strategy_stats[strategy]["losses"] += 1
    
    def get_win_rate(self, strategy):
        stats = self.strategy_stats[strategy]
        total = stats["wins"] + stats["losses"]
        return stats["wins"] / total if total > 0 else 0.5


class SafeRiskManager:
    """Strict risk management - Balance Protection"""
    
    def __init__(self, config):
        self.config = config
        self.daily_pnl = 0
        self.total_trades = 0
        self.last_reset = datetime.now().date()
        self.halted = False
    
    def reset_daily(self):
        today = datetime.now().date()
        if today != self.last_reset:
            logger.info(f"Daily P&L Reset | Yesterday: ${self.daily_pnl:.2f}")
            self.daily_pnl = 0
            self.total_trades = 0
            self.last_reset = today
            self.halted = False
    
    def check_daily_loss_limit(self):
        self.reset_daily()
        loss_limit = self.config.TOTAL_BALANCE * self.config.DAILY_LOSS_LIMIT_PCT
        
        if self.daily_pnl < -loss_limit:
            if not self.halted:
                logger.critical(f"LOSS LIMIT REACHED! Daily P&L: ${self.daily_pnl:.2f}")
                self.halted = True
            return False
        
        return True
    
    def update_pnl(self, pnl):
        self.daily_pnl += pnl
        self.total_trades += 1
        
        if pnl > 0:
            logger.info(f"Profit: +${pnl:.2f} | Daily Total: ${self.daily_pnl:.2f}")
        else:
            logger.warning(f"Loss: ${pnl:.2f} | Daily Total: ${self.daily_pnl:.2f}")


class PositionManager:
    """Position management with strategy-aware SL/TP"""
    
    def __init__(self, config, client, risk_manager, strategy_engine):
        self.config = config
        self.client = client
        self.risk_manager = risk_manager
        self.strategy_engine = strategy_engine
        self.active_positions = {}
    
    def monitor_positions(self):
        positions = self.client.get_positions()
        
        for position in positions:
            contract = position.contract
            size = int(position.size or 0)
            if size == 0:
                if contract in self.active_positions:
                    del self.active_positions[contract]
                continue
            
            entry_price = float(position.entry_price or 0)
            current_price = self.client.get_price(contract)
            if not current_price:
                continue
            
            pos_data = self.active_positions.get(contract, {})
            
            if 'stop_loss' not in pos_data or 'take_profit' not in pos_data:
                strategy = pos_data.get('strategy', Strategy.SCALPING)
                tp_pct = pos_data.get('tp_pct', self.config.SCALP_TARGET_PCT)
                sl_pct = pos_data.get('sl_pct', self.config.SCALP_STOP_LOSS_PCT)
                
                if size < 0:
                    stop_loss = entry_price * (1 + sl_pct)
                    take_profit = entry_price * (1 - tp_pct)
                else:
                    stop_loss = entry_price * (1 - sl_pct)
                    take_profit = entry_price * (1 + tp_pct)
                
                self.active_positions[contract] = {
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'size': size,
                    'strategy': strategy,
                    'tp_pct': tp_pct,
                    'sl_pct': sl_pct
                }
                logger.info(f"Position tracked [{strategy.value}]: {contract} | SL: ${stop_loss:.4f} | TP: ${take_profit:.4f}")
            
            pos_info = self.active_positions[contract]
            strategy = pos_info.get('strategy', Strategy.SCALPING)
            pnl = 0
            
            if size < 0:
                if current_price >= pos_info['stop_loss']:
                    logger.warning(f"STOP LOSS hit on {contract} [{strategy.value}]! Closing...")
                    self.client.close_position(contract, size)
                    pnl = (pos_info['entry_price'] - current_price) * abs(size)
                    self.risk_manager.update_pnl(pnl)
                    self.strategy_engine.record_result(strategy, won=False)
                    del self.active_positions[contract]
                
                elif current_price <= pos_info['take_profit']:
                    logger.info(f"TAKE PROFIT hit on {contract} [{strategy.value}]! Closing...")
                    self.client.close_position(contract, size)
                    pnl = (pos_info['entry_price'] - current_price) * abs(size)
                    self.risk_manager.update_pnl(pnl)
                    self.strategy_engine.record_result(strategy, won=True)
                    del self.active_positions[contract]
    
    def set_position_params(self, contract, strategy, tp_pct, sl_pct):
        """Set position parameters for new position"""
        self.active_positions[contract] = {
            'strategy': strategy,
            'tp_pct': tp_pct,
            'sl_pct': sl_pct
        }


class MultiStrategyEngine:
    """Multi-Strategy Trading Engine with AI Integration"""
    
    def __init__(self, config, client, ai, strategy_engine, position_manager):
        self.config = config
        self.client = client
        self.ai = ai
        self.strategy_engine = strategy_engine
        self.position_manager = position_manager
        self.trades = 0
        self.last_trade = {}
        self.day = datetime.now().date()
        self.pending_entries = {}
    
    def reset(self):
        today = datetime.now().date()
        if today != self.day:
            logger.info(f"Daily trades reset | Yesterday: {self.trades}")
            self.trades = 0
            self.day = today
    
    def can_trade(self, contract):
        self.reset()
        if self.trades >= self.config.SCALP_MAX_TRADES:
            return False, "Max trades reached"
        last = self.last_trade.get(contract, 0)
        if time.time() - last < self.config.TRADE_COOLDOWN_SEC:
            return False, "Cooldown"
        return True, "Ready"
    
    def get_position_size(self, contract, price):
        info = self.client.get_contract_info(contract)
        if not info:
            return 1
        
        quanto = float(info.quanto_multiplier or 1)
        capital = self.config.TOTAL_BALANCE * self.config.MAX_POSITION_SIZE_PCT
        risk_capital = capital * self.config.MAX_LEVERAGE
        
        if quanto > 0:
            size = int(risk_capital / (price * quanto))
        else:
            size = int(risk_capital / price)
        
        return max(1, min(size, 5))
    
    def execute(self, contract, price, funding, volatility=0.015, adx=25):
        can, reason = self.can_trade(contract)
        if not can:
            return None, reason
        
        strategy, strategy_reason = self.strategy_engine.select_strategy(adx, funding, volatility)
        
        analysis = self.ai.analyze(contract, price, funding, volatility, adx, strategy)
        
        if analysis["go"]:
            base_size = self.get_position_size(contract, price)
            entries = self.strategy_engine.get_entry_params(strategy, base_size, price)
            
            symbol = contract.replace("_", "/")
            
            logger.info("=" * 60)
            logger.info(f"STRATEGY: {strategy.value} | {strategy_reason}")
            logger.info(f"AI Consensus: {analysis['votes']}/6 | Score: {analysis['score']:.0f}")
            logger.info("=" * 60)
            
            total_filled = 0
            for i, entry in enumerate(entries):
                entry_price = price * (1 + entry.get('entry_offset', 0))
                size = entry['size']
                
                if i == 0:
                    logger.info(f"[Layer {i+1}] SHORT {symbol}: {size} @ ${entry_price:,.4f}")
                    
                    result = self.client.place_short(contract, size)
                    if result:
                        total_filled += 1
                        
                        tp = entry_price * (1 - entry['tp_pct'])
                        sl = entry_price * (1 + entry['sl_pct'])
                        logger.info(f"  TP: ${tp:,.4f} ({entry['tp_pct']*100:.1f}%) | SL: ${sl:,.4f} ({entry['sl_pct']*100:.1f}%)")
                        
                        self.position_manager.set_position_params(
                            contract, strategy, entry['tp_pct'], entry['sl_pct']
                        )
                else:
                    self.pending_entries[f"{contract}_{i}"] = {
                        "contract": contract,
                        "layer": i + 1,
                        "trigger_price": entry_price,
                        "size": size,
                        "strategy": strategy,
                        "tp_pct": entry['tp_pct'],
                        "sl_pct": entry['sl_pct'],
                        "created": time.time()
                    }
                    logger.info(f"[Layer {i+1}] Pending @ ${entry_price:,.4f} (waiting for price)")
            
            if total_filled > 0:
                self.trades += 1
                self.last_trade[contract] = time.time()
                return True, f"FILLED ({strategy.value})"
            
            return None, "Order failed"
        
        return None, f"No signal [{strategy.value}] (Votes: {analysis['votes']}, Score: {analysis['score']:.0f})"
    
    def check_pending_entries(self):
        """Check and execute pending layer entries"""
        current_prices = {}
        to_remove = []
        
        for key, entry in self.pending_entries.items():
            contract = entry['contract']
            
            if contract not in current_prices:
                current_prices[contract] = self.client.get_price(contract)
            
            price = current_prices[contract]
            if not price:
                continue
            
            if time.time() - entry['created'] > 3600:
                to_remove.append(key)
                continue
            
            if price >= entry['trigger_price']:
                logger.info(f"[Layer {entry['layer']}] Triggered @ ${price:,.4f}")
                result = self.client.place_short(contract, entry['size'])
                
                if result:
                    tp = price * (1 - entry['tp_pct'])
                    sl = price * (1 + entry['sl_pct'])
                    logger.info(f"  Layer {entry['layer']} FILLED | TP: ${tp:,.4f} | SL: ${sl:,.4f}")
                    self.trades += 1
                
                to_remove.append(key)
        
        for key in to_remove:
            del self.pending_entries[key]


class SafeTradingBot:
    def __init__(self, config):
        self.config = config
        self.client = GateClient(config)
        self.scanner = PairScanner(config, self.client)
        self.ai = AIEngine()
        self.risk_manager = SafeRiskManager(config)
        self.strategy_engine = StrategyEngine(config)
        self.position_manager = PositionManager(config, self.client, self.risk_manager, self.strategy_engine)
        self.engine = MultiStrategyEngine(config, self.client, self.ai, self.strategy_engine, self.position_manager)
        self.running = False
        self.cycle = 0
        self.current_pairs = []
    
    def run(self):
        logger.info("=" * 70)
        logger.info("TRADING GURU - MULTI-STRATEGY AI SYSTEM")
        logger.info("=" * 70)
        logger.info(f"Balance: ${self.config.TOTAL_BALANCE}")
        logger.info(f"Leverage: {self.config.MAX_LEVERAGE}x")
        logger.info(f"Position Size: {self.config.MAX_POSITION_SIZE_PCT*100}%")
        logger.info(f"Daily Loss Limit: {self.config.DAILY_LOSS_LIMIT_PCT*100}%")
        logger.info(f"Max Trades/Day: {self.config.SCALP_MAX_TRADES}")
        logger.info("")
        logger.info("STRATEGIES ACTIVE:")
        logger.info(f"  SCALPING: ADX < {self.config.ADX_RANGE} (TP: {self.config.SCALP_TARGET_PCT*100}%)")
        logger.info(f"  WATERFALL: ADX {self.config.ADX_TREND}-{self.config.ADX_HYPER_TREND} ({self.config.WATERFALL_ENTRIES} layers, TP: {self.config.WATERFALL_TP_PCT*100}%)")
        logger.info(f"  SNOWBALL: Funding > {self.config.SNOWBALL_MIN_FUNDING*100}% (Hold: {self.config.SNOWBALL_HOLD_HOURS}h)")
        logger.info(f"  PYRAMID: ADX > {self.config.ADX_HYPER_TREND} ({self.config.PYRAMID_ENTRIES} layers, {self.config.PYRAMID_MULTIPLIER}x mult)")
        logger.info("")
        logger.info(f"AI Consensus: {self.config.MIN_AI_VOTES}/6 votes, {self.config.MIN_SCORE}+ score")
        logger.info("Direction: SHORTS ONLY")
        logger.info("=" * 70)
        
        logger.info("\nScanning for best profitable pairs...")
        self.scanner.display_rankings()
        
        self.running = True
        
        try:
            while self.running:
                self.loop()
                time.sleep(self.config.LOOP_DELAY_SEC)
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.critical(f"Error: {e}")
    
    def loop(self):
        self.cycle += 1
        
        if not self.risk_manager.check_daily_loss_limit():
            if self.cycle % 100 == 0:
                logger.info("HALTED - Daily loss limit reached. Waiting for reset...")
            return
        
        self.position_manager.monitor_positions()
        
        self.engine.check_pending_entries()
        
        best_pairs = self.scanner.get_best_pairs(top_n=3)
        
        if not best_pairs:
            return
        
        if self.cycle % 30 == 1:
            pair_names = [p["contract"] for p in best_pairs]
            if pair_names != self.current_pairs:
                self.current_pairs = pair_names
                logger.info(f"Active pairs: {', '.join(pair_names)}")
        
        for pair_info in best_pairs:
            contract = pair_info["contract"]
            price = pair_info["price"]
            funding = pair_info["funding"]
            volatility = pair_info["volatility"]
            adx = pair_info["adx"]
            
            result, msg = self.engine.execute(contract, price, funding, volatility, adx)
            if result:
                logger.info(f"Trade {contract}: {msg}")
        
        if self.cycle % 30 == 0:
            account = self.client.get_account()
            bal = float(account.available) if account else 0
            pnl = float(account.unrealised_pnl or 0) if account else 0
            
            strategy = self.strategy_engine.current_strategy.value
            
            logger.info(f"Cycle {self.cycle} | Strategy: {strategy} | Bal: ${bal:.2f} | PNL: ${pnl:.2f} | Daily: ${self.risk_manager.daily_pnl:.2f} | Trades: {self.engine.trades}/{self.config.SCALP_MAX_TRADES}")
        
        if self.cycle % 90 == 0:
            self.scanner.display_rankings()
            
            logger.info("\n--- Strategy Performance ---")
            for strategy in Strategy:
                stats = self.strategy_engine.strategy_stats[strategy]
                wr = self.strategy_engine.get_win_rate(strategy)
                logger.info(f"{strategy.value}: {stats['wins']}W / {stats['losses']}L ({wr*100:.0f}% WR)")
            logger.info("----------------------------\n")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TRADING GURU - MULTI-STRATEGY AI SYSTEM")
    print("WATERFALL | SNOWBALL | PYRAMID | SCALPING")
    print("SHORTS ONLY - Dynamic Strategy Selection")
    print("=" * 70 + "\n")
    
    config = SafeConfig()
    
    if not config.API_KEY:
        print("ERROR: Set GATE_API_KEY!")
        exit(1)
    
    bot = SafeTradingBot(config)
    bot.run()
