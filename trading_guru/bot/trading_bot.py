"""
Trading Guru Bot - AI-Powered Smart Trading Bot for Gate.io Futures
SHORTS ONLY - Grid Trading + Scalping + Martingale Hybrid Strategy

Version: 2.0.0 (Real Trading Mode)
"""

import gate_api
from gate_api.exceptions import ApiException, GateApiException
import time
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('TradingGuruBot')


class BotConfig:
    """Bot configuration - REAL TRADING MODE"""
    
    # API Configuration (from Replit Secrets)
    API_KEY = os.environ.get('GATE_API_KEY', '')
    API_SECRET = os.environ.get('GATE_API_SECRET', '')
    HOST = "https://api.gateio.ws/api/v4"
    
    # Trading Parameters
    SETTLE = "usdt"
    CONTRACT = "BTC_USDT"
    TRADING_DIRECTION = "SHORTS_ONLY"
    
    # Capital Allocation
    TOTAL_BALANCE = float(os.environ.get('TOTAL_BALANCE', '1000'))
    GRID_ALLOCATION = 0.60
    SCALP_ALLOCATION = 0.30
    MARTINGALE_RESERVE = 0.10
    
    # Grid Trading Parameters
    GRID_COUNT = 15
    GRID_RANGE_PCT = 0.04
    
    # Scalping Parameters
    SCALP_TARGET_PCT = 0.005
    SCALP_STOP_LOSS_PCT = 0.0025
    SCALP_MAX_TRADES_PER_DAY = 50
    
    # Martingale Parameters
    MARTINGALE_MAX_CYCLES = 4
    MARTINGALE_INITIAL_SIZE = 0.01
    
    # Risk Management
    MAX_LEVERAGE = 5
    MAX_POSITION_SIZE_PCT = 0.02
    DAILY_LOSS_LIMIT_PCT = 0.05
    STOP_LOSS_MANDATORY = True
    
    # Loop Parameters
    LOOP_DELAY_MS = 1000
    
    # AI Consensus
    MIN_AI_VOTES_FOR_TRADE = 4
    MIN_CONFLUENCE_SCORE = 75
    
    # Fees
    MAKER_FEE = 0.0009
    TAKER_FEE = 0.0009


class GateIOClient:
    """Gate.io Futures API Client"""
    
    def __init__(self, api_key: str, api_secret: str, host: str):
        self.configuration = gate_api.Configuration(
            key=api_key,
            secret=api_secret,
            host=host
        )
        self.api_client = gate_api.ApiClient(self.configuration)
        self.futures_api = gate_api.FuturesApi(self.api_client)
        logger.info("Gate.io client initialized")
    
    def get_futures_account(self, settle: str) -> Dict:
        """Get futures account information"""
        try:
            account = self.futures_api.list_futures_accounts(settle)
            return account
        except GateApiException as ex:
            logger.error(f"Gate API Exception: {ex}")
            return None
    
    def get_current_price(self, settle: str, contract: str) -> float:
        """Get current market price"""
        try:
            ticker = self.futures_api.list_futures_tickers(settle, contract=contract)
            if ticker and len(ticker) > 0:
                return float(ticker[0].last)
            return None
        except GateApiException as ex:
            logger.error(f"Error getting price: {ex}")
            return None
    
    def get_funding_rate(self, settle: str, contract: str) -> float:
        """Get current funding rate"""
        try:
            ticker = self.futures_api.list_futures_tickers(settle, contract=contract)
            if ticker and len(ticker) > 0:
                return float(ticker[0].funding_rate or 0)
            return 0.0
        except GateApiException as ex:
            logger.error(f"Error getting funding rate: {ex}")
            return 0.0
    
    def place_short_order(self, settle: str, contract: str, size: int, 
                          price: float = None, tif: str = 'gtc') -> Dict:
        """Place a SHORT order (size must be negative)"""
        try:
            order = gate_api.FuturesOrder(
                contract=contract,
                size=-abs(size),
                price=str(price) if price else "0",
                tif=tif if price else "ioc"
            )
            result = self.futures_api.create_futures_order(settle, order)
            logger.info(f"SHORT order placed: {result}")
            return result
        except GateApiException as ex:
            logger.error(f"Error placing SHORT order: {ex}")
            return None
    
    def get_positions(self, settle: str) -> List:
        """Get all open positions"""
        try:
            positions = self.futures_api.list_positions(settle)
            return positions
        except GateApiException as ex:
            logger.error(f"Error getting positions: {ex}")
            return []
    
    def close_position(self, settle: str, contract: str, size: int):
        """Close a position"""
        try:
            order = gate_api.FuturesOrder(
                contract=contract,
                size=abs(size),
                price="0",
                tif="ioc",
                reduce_only=True
            )
            result = self.futures_api.create_futures_order(settle, order)
            logger.info(f"Position closed: {result}")
            return result
        except GateApiException as ex:
            logger.error(f"Error closing position: {ex}")
            return None


class AIPredictor:
    """AI-powered price prediction using 6 agents"""
    
    def __init__(self):
        try:
            from trading_guru.agents.llm_agent import get_multi_agent_consensus
            from trading_guru.core.models import MarketData
            self.get_consensus = get_multi_agent_consensus
            self.MarketData = MarketData
            self.ai_enabled = True
            logger.info("AI Predictor initialized with 6 agents")
        except ImportError as e:
            logger.warning(f"AI agents not available: {e}")
            self.ai_enabled = False
    
    def predict(self, symbol: str, price: float, volume: float = 0, 
                atr: float = 0, adx: float = 25, funding_rate: float = 0) -> Dict:
        """Get AI prediction for SHORT opportunities"""
        
        if not self.ai_enabled:
            return {"direction": "NEUTRAL", "score": 0, "votes": 0}
        
        try:
            market_data = self.MarketData(
                symbol=symbol,
                price=price,
                volume_24h=volume,
                volatility_atr=atr if atr > 0 else price * 0.02,
                adx_14=adx,
                spread_percent=0.001,
                funding_rate=funding_rate,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            result = self.get_consensus(market_data, "Trinity of Profit - SHORTS ONLY")
            
            return {
                "direction": result["consensus"].upper(),
                "score": result["avg_score"],
                "votes": result["short_votes"],
                "strategy": result["best_signal"].strategy if result["best_signal"] else "scalping"
            }
        except Exception as e:
            logger.error(f"AI prediction error: {e}")
            return {"direction": "NEUTRAL", "score": 0, "votes": 0}


class GridStrategy:
    """Grid Trading Strategy - SHORTS ONLY"""
    
    def __init__(self, config: BotConfig, client: GateIOClient):
        self.config = config
        self.client = client
        self.grid_orders = []
        self.base_price = None
    
    def initialize_grid(self, current_price: float):
        """Initialize SHORT grid levels above current price"""
        self.base_price = current_price
        self.grid_orders = []
        grid_size = (self.config.GRID_RANGE_PCT * current_price) / self.config.GRID_COUNT
        
        logger.info(f"Initializing SHORT grid at base price: {current_price}")
        
        for i in range(self.config.GRID_COUNT):
            price = current_price + (i + 1) * grid_size
            self.grid_orders.append({
                'level': i,
                'price': price,
                'type': 'SHORT',
                'active': False,
                'filled': False
            })
            logger.info(f"  Grid {i+1}: SHORT at ${price:,.2f}")
    
    def execute(self, current_price: float, ai_prediction: Dict) -> Optional[Dict]:
        """Execute grid strategy - SHORTS ONLY"""
        if not self.base_price:
            self.initialize_grid(current_price)
            return None
        
        price_change_pct = abs(current_price - self.base_price) / self.base_price
        if price_change_pct > 0.03:
            logger.info("Price moved >3%, reinitializing grid")
            self.initialize_grid(current_price)
            return None
        
        for grid in self.grid_orders:
            if not grid['filled'] and current_price >= grid['price']:
                if ai_prediction.get('direction') == 'SHORT' and ai_prediction.get('score', 0) >= 70:
                    grid['filled'] = True
                    logger.info(f"Grid level {grid['level']+1} triggered at ${grid['price']:,.2f}")
                    return {
                        'action': 'SHORT',
                        'price': grid['price'],
                        'level': grid['level'],
                        'strategy': 'GRID'
                    }
        
        return None


class ScalpingStrategy:
    """Scalping Strategy - SHORTS ONLY with AI"""
    
    def __init__(self, config: BotConfig, client: GateIOClient):
        self.config = config
        self.client = client
        self.trades_today = 0
        self.last_reset = datetime.now().date()
    
    def reset_daily_counter(self):
        """Reset daily trade counter"""
        today = datetime.now().date()
        if today != self.last_reset:
            self.trades_today = 0
            self.last_reset = today
    
    def execute(self, current_price: float, ai_prediction: Dict) -> Optional[Dict]:
        """Execute scalping - SHORTS ONLY"""
        self.reset_daily_counter()
        
        if self.trades_today >= self.config.SCALP_MAX_TRADES_PER_DAY:
            logger.info("Daily scalping limit reached")
            return None
        
        if ai_prediction.get('direction') == 'SHORT':
            if ai_prediction.get('score', 0) >= self.config.MIN_CONFLUENCE_SCORE:
                if ai_prediction.get('votes', 0) >= self.config.MIN_AI_VOTES_FOR_TRADE:
                    self.trades_today += 1
                    
                    return {
                        'action': 'SHORT',
                        'price': current_price,
                        'score': ai_prediction['score'],
                        'votes': ai_prediction['votes'],
                        'strategy': 'SCALPING'
                    }
        
        return None


class MartingaleStrategy:
    """Limited Martingale Recovery - SHORTS ONLY"""
    
    def __init__(self, config: BotConfig, client: GateIOClient):
        self.config = config
        self.client = client
        self.active_cycles = {}
    
    def should_apply(self, position: Dict) -> bool:
        """Check if martingale should be applied"""
        if not position:
            return False
        
        unrealized_pnl = float(getattr(position, 'unrealised_pnl', 0) or 0)
        size = int(getattr(position, 'size', 0) or 0)
        
        return unrealized_pnl < 0 and size < 0
    
    def execute(self, position: Dict, current_price: float) -> Optional[Dict]:
        """Execute martingale recovery - SHORTS ONLY"""
        contract = getattr(position, 'contract', '')
        
        if contract not in self.active_cycles:
            self.active_cycles[contract] = 0
        
        cycle = self.active_cycles[contract]
        
        if cycle >= self.config.MARTINGALE_MAX_CYCLES:
            logger.warning(f"Max martingale cycles ({cycle}) reached for {contract}")
            return None
        
        current_size = abs(int(getattr(position, 'size', 0) or 0))
        new_size = current_size
        
        self.active_cycles[contract] += 1
        
        logger.info(f"Martingale cycle {cycle + 1} for {contract}: adding {new_size} contracts")
        
        return {
            'action': 'SHORT',
            'price': current_price,
            'size': new_size,
            'cycle': cycle + 1,
            'strategy': 'MARTINGALE'
        }
    
    def reset_cycle(self, contract: str):
        """Reset martingale cycle after profitable exit"""
        if contract in self.active_cycles:
            self.active_cycles[contract] = 0


class RiskManager:
    """Risk management - protects capital"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.daily_pnl = 0.0
        self.last_reset = datetime.now().date()
        self.trade_count = 0
    
    def reset_daily_pnl(self):
        """Reset daily P&L"""
        today = datetime.now().date()
        if today != self.last_reset:
            self.daily_pnl = 0.0
            self.trade_count = 0
            self.last_reset = today
            logger.info("Daily P&L reset")
    
    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit exceeded"""
        self.reset_daily_pnl()
        loss_limit = self.config.TOTAL_BALANCE * self.config.DAILY_LOSS_LIMIT_PCT
        
        if self.daily_pnl < -loss_limit:
            logger.critical(f"DAILY LOSS LIMIT REACHED: ${self.daily_pnl:,.2f}")
            return False
        
        return True
    
    def update_pnl(self, pnl: float):
        """Update daily P&L"""
        self.daily_pnl += pnl
        self.trade_count += 1
        logger.info(f"Trade P&L: ${pnl:,.2f} | Daily Total: ${self.daily_pnl:,.2f}")
    
    def calculate_position_size(self, price: float, strategy: str) -> int:
        """Calculate position size based on strategy"""
        if strategy == 'GRID':
            capital = self.config.TOTAL_BALANCE * self.config.GRID_ALLOCATION
        elif strategy == 'SCALPING':
            capital = self.config.TOTAL_BALANCE * self.config.SCALP_ALLOCATION
        else:
            capital = self.config.TOTAL_BALANCE * self.config.MARTINGALE_RESERVE
        
        position_usd = capital * self.config.MAX_POSITION_SIZE_PCT
        position_size = int((position_usd * self.config.MAX_LEVERAGE) / price)
        
        return max(1, position_size)


class TradingGuruBot:
    """Main Trading Guru Bot - SHORTS ONLY"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.client = GateIOClient(config.API_KEY, config.API_SECRET, config.HOST)
        self.ai_predictor = AIPredictor()
        self.grid_strategy = GridStrategy(config, self.client)
        self.scalp_strategy = ScalpingStrategy(config, self.client)
        self.martingale_strategy = MartingaleStrategy(config, self.client)
        self.risk_manager = RiskManager(config)
        self.running = False
        self.cycle_count = 0
    
    def start(self):
        """Start the trading bot"""
        logger.info("=" * 80)
        logger.info("TRADING GURU BOT - REAL TRADING MODE")
        logger.info("=" * 80)
        logger.info(f"Direction: {self.config.TRADING_DIRECTION}")
        logger.info(f"Contract: {self.config.CONTRACT}")
        logger.info(f"Balance: ${self.config.TOTAL_BALANCE:,.2f}")
        logger.info(f"Max Leverage: {self.config.MAX_LEVERAGE}x")
        logger.info(f"Daily Loss Limit: {self.config.DAILY_LOSS_LIMIT_PCT * 100}%")
        logger.info("=" * 80)
        
        self.running = True
        
        try:
            while self.running:
                self.main_loop()
                time.sleep(self.config.LOOP_DELAY_MS / 1000)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            self.stop()
        except Exception as ex:
            logger.critical(f"Critical error: {ex}")
            self.stop()
    
    def main_loop(self):
        """Main trading loop"""
        self.cycle_count += 1
        
        if not self.risk_manager.check_daily_loss_limit():
            logger.warning("Daily loss limit exceeded - STOPPING")
            self.stop()
            return
        
        current_price = self.client.get_current_price(self.config.SETTLE, self.config.CONTRACT)
        if not current_price:
            logger.error("Failed to get current price")
            return
        
        funding_rate = self.client.get_funding_rate(self.config.SETTLE, self.config.CONTRACT)
        
        ai_prediction = self.ai_predictor.predict(
            symbol=self.config.CONTRACT.replace("_", "/"),
            price=current_price,
            funding_rate=funding_rate * 100
        )
        
        scalp_signal = self.scalp_strategy.execute(current_price, ai_prediction)
        if scalp_signal:
            self.execute_trade(scalp_signal, current_price)
        
        grid_signal = self.grid_strategy.execute(current_price, ai_prediction)
        if grid_signal:
            self.execute_trade(grid_signal, current_price)
        
        positions = self.client.get_positions(self.config.SETTLE)
        for position in positions:
            if self.martingale_strategy.should_apply(position):
                martingale_signal = self.martingale_strategy.execute(position, current_price)
                if martingale_signal:
                    self.execute_trade(martingale_signal, current_price)
        
        if self.cycle_count % 60 == 0:
            logger.info(f"Cycle {self.cycle_count} | Price: ${current_price:,.2f} | "
                       f"Funding: {funding_rate*100:.4f}% | AI: {ai_prediction.get('direction')} "
                       f"(Score: {ai_prediction.get('score', 0):.0f}, Votes: {ai_prediction.get('votes', 0)}/6)")
    
    def execute_trade(self, signal: Dict, current_price: float):
        """Execute a SHORT trade"""
        if signal['action'] != 'SHORT':
            logger.warning(f"Ignoring non-SHORT signal: {signal['action']}")
            return
        
        strategy = signal.get('strategy', 'UNKNOWN')
        size = signal.get('size') or self.risk_manager.calculate_position_size(current_price, strategy)
        
        logger.info(f"EXECUTING SHORT | Strategy: {strategy} | Size: {size} | Price: ${current_price:,.2f}")
        
        result = self.client.place_short_order(
            self.config.SETTLE,
            self.config.CONTRACT,
            size,
            None
        )
        
        if result:
            logger.info(f"SHORT order executed successfully")
        else:
            logger.error("SHORT order failed")
    
    def stop(self):
        """Stop the bot"""
        logger.info("Stopping Trading Guru Bot...")
        self.running = False
        logger.info(f"Final Daily P&L: ${self.risk_manager.daily_pnl:,.2f}")
        logger.info(f"Total Trades: {self.risk_manager.trade_count}")
        logger.info("Bot stopped")


def run_bot():
    """Entry point to run the bot"""
    config = BotConfig()
    
    if not config.API_KEY or not config.API_SECRET:
        logger.error("GATE_API_KEY and GATE_API_SECRET must be set in environment!")
        logger.error("Add them to Replit Secrets")
        return
    
    bot = TradingGuruBot(config)
    bot.start()


if __name__ == "__main__":
    run_bot()
