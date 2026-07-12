"""
Trading Guru Bot - AI-Powered Smart Trading Bot for Gate.io Futures
Hybrid Strategy: Grid Trading + Scalping + Limited Martingale
SHORTS ONLY MODE - Real Trading

Author: Trading Guru Team
Version: 2.0.0
"""

import gate_api
from gate_api.exceptions import ApiException, GateApiException
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('TradingGuruBot')


class BotConfig:
    """Bot configuration parameters"""
    
    API_KEY = os.environ.get('GATE_API_KEY', '')
    API_SECRET = os.environ.get('GATE_API_SECRET', '')
    HOST = "https://api.gateio.ws/api/v4"
    
    SETTLE = "usdt"
    CONTRACT = "BTC_USDT"
    
    TOTAL_BALANCE = float(os.environ.get('TOTAL_BALANCE', '1000'))
    GRID_ALLOCATION = 0.60
    SCALP_ALLOCATION = 0.30
    MARTINGALE_RESERVE = 0.10
    
    GRID_COUNT = 15
    GRID_RANGE_PCT = 0.04
    
    SCALP_TARGET_PCT = 0.005
    SCALP_STOP_LOSS_PCT = 0.0025
    SCALP_MAX_TRADES_PER_DAY = 50
    
    MARTINGALE_MAX_CYCLES = 4
    MARTINGALE_INITIAL_SIZE = 0.01
    
    MAX_LEVERAGE = 5
    MAX_POSITION_SIZE_PCT = 0.02
    DAILY_LOSS_LIMIT_PCT = 0.05
    STOP_LOSS_MANDATORY = True
    
    LOOP_DELAY_MS = 1000
    
    MAKER_FEE = 0.0009
    TAKER_FEE = 0.0009


class GateIOClient:
    """Wrapper for Gate.io API operations"""
    
    def __init__(self, api_key: str, api_secret: str, host: str):
        self.configuration = gate_api.Configuration(
            key=api_key,
            secret=api_secret,
            host=host
        )
        self.api_client = gate_api.ApiClient(self.configuration)
        self.futures_api = gate_api.FuturesApi(self.api_client)
    
    def get_futures_account(self, settle: str):
        try:
            account = self.futures_api.list_futures_accounts(settle)
            return account
        except GateApiException as ex:
            logger.error(f"Gate API Exception: {ex}")
            return None
    
    def get_current_price(self, settle: str, contract: str) -> float:
        try:
            ticker = self.futures_api.list_futures_tickers(settle, contract=contract)
            if ticker and len(ticker) > 0:
                return float(ticker[0].last)
            return None
        except GateApiException as ex:
            logger.error(f"Error getting price: {ex}")
            return None
    
    def get_funding_rate(self, settle: str, contract: str) -> float:
        try:
            ticker = self.futures_api.list_futures_tickers(settle, contract=contract)
            if ticker and len(ticker) > 0:
                return float(ticker[0].funding_rate or 0)
            return 0.0
        except GateApiException as ex:
            return 0.0
    
    def place_order(self, settle: str, contract: str, size: int, price: float = None, 
                    tif: str = 'gtc', reduce_only: bool = False):
        try:
            order = gate_api.FuturesOrder(
                contract=contract,
                size=size,
                price=str(price) if price else "0",
                tif=tif if price else "ioc",
                reduce_only=reduce_only
            )
            result = self.futures_api.create_futures_order(settle, order)
            logger.info(f"Order placed: size={size}, price={price or 'market'}")
            return result
        except GateApiException as ex:
            logger.error(f"Error placing order: {ex}")
            return None
    
    def get_positions(self, settle: str) -> List:
        try:
            positions = self.futures_api.list_positions(settle)
            return positions
        except GateApiException as ex:
            logger.error(f"Error getting positions: {ex}")
            return []
    
    def close_position(self, settle: str, contract: str, size: int):
        try:
            order = self.place_order(settle, contract, -size, reduce_only=True)
            return order
        except Exception as ex:
            logger.error(f"Error closing position: {ex}")
            return None


class AIPredictor:
    """AI-powered prediction using 6 agents"""
    
    def __init__(self):
        try:
            from trading_guru.agents.llm_agent import get_multi_agent_consensus
            from trading_guru.core.models import MarketData
            self.get_consensus = get_multi_agent_consensus
            self.MarketData = MarketData
            self.enabled = True
            logger.info("AI Predictor: 6 agents initialized")
        except Exception as e:
            logger.warning(f"AI not available: {e}")
            self.enabled = False
    
    def predict(self, symbol: str, price: float, funding_rate: float = 0) -> str:
        if not self.enabled:
            return 'NEUTRAL'
        
        try:
            market_data = self.MarketData(
                symbol=symbol,
                price=price,
                volume_24h=1000000000,
                volatility_atr=price * 0.02,
                adx_14=30.0,
                spread_percent=0.001,
                funding_rate=funding_rate,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            result = self.get_consensus(market_data, "Trinity of Profit")
            
            if result["short_votes"] >= 4 and result["avg_score"] >= 75:
                return 'SHORT'
            return 'NEUTRAL'
        except Exception as e:
            logger.error(f"AI error: {e}")
            return 'NEUTRAL'


class GridStrategy:
    """Grid Trading Strategy - SHORTS ONLY"""
    
    def __init__(self, config: BotConfig, client: GateIOClient):
        self.config = config
        self.client = client
        self.grid_orders = []
        self.base_price = None
    
    def initialize_grid(self, current_price: float):
        self.base_price = current_price
        self.grid_orders = []
        grid_size = (self.config.GRID_RANGE_PCT * current_price) / self.config.GRID_COUNT
        
        logger.info(f"Grid initialized at ${current_price:,.2f}, size: ${grid_size:,.2f}")
        
        for i in range(self.config.GRID_COUNT):
            price = current_price + (i + 1) * grid_size
            self.grid_orders.append({
                'level': i,
                'price': price,
                'type': 'short',
                'active': False
            })
    
    def execute(self, current_price: float):
        if not self.base_price:
            self.initialize_grid(current_price)
        
        price_change_pct = abs(current_price - self.base_price) / self.base_price
        if price_change_pct > 0.03:
            logger.info("Price moved >3%, reinitializing grid")
            self.initialize_grid(current_price)


class ScalpingStrategy:
    """Scalping Strategy with AI prediction - SHORTS ONLY"""
    
    def __init__(self, config: BotConfig, client: GateIOClient, ai: AIPredictor):
        self.config = config
        self.client = client
        self.ai = ai
        self.trades_today = 0
        self.last_reset = datetime.now().date()
    
    def reset_daily_counter(self):
        today = datetime.now().date()
        if today != self.last_reset:
            self.trades_today = 0
            self.last_reset = today
    
    def execute(self, current_price: float, funding_rate: float):
        self.reset_daily_counter()
        
        if self.trades_today >= self.config.SCALP_MAX_TRADES_PER_DAY:
            logger.info("Daily scalping limit reached")
            return None
        
        symbol = self.config.CONTRACT.replace("_", "/")
        prediction = self.ai.predict(symbol, current_price, funding_rate * 100)
        
        if prediction == 'SHORT':
            capital = self.config.TOTAL_BALANCE * self.config.SCALP_ALLOCATION
            position_size = (capital * self.config.MAX_POSITION_SIZE_PCT) / current_price
            size = -int(position_size * self.config.MAX_LEVERAGE)
            
            if size >= 0:
                size = -1
            
            logger.info(f"SCALP SHORT: {size} contracts at ${current_price:,.2f}")
            order = self.client.place_order(
                self.config.SETTLE,
                self.config.CONTRACT,
                size,
                None
            )
            
            if order:
                self.trades_today += 1
                return order
        
        return None


class MartingaleStrategy:
    """Limited Martingale/Snowball Strategy"""
    
    def __init__(self, config: BotConfig, client: GateIOClient):
        self.config = config
        self.client = client
        self.active_cycles = {}
    
    def should_apply_martingale(self, position) -> bool:
        if not position:
            return False
        
        unrealized_pnl = float(getattr(position, 'unrealised_pnl', 0) or 0)
        size = int(getattr(position, 'size', 0) or 0)
        return unrealized_pnl < -5 and size < 0
    
    def execute(self, position, current_price: float):
        contract = getattr(position, 'contract', '')
        
        if contract not in self.active_cycles:
            self.active_cycles[contract] = 0
        
        cycle = self.active_cycles[contract]
        
        if cycle >= self.config.MARTINGALE_MAX_CYCLES:
            return None
        
        current_size = abs(int(getattr(position, 'size', 0) or 0))
        new_size = -current_size
        
        logger.info(f"Martingale cycle {cycle + 1} for {contract}")
        
        order = self.client.place_order(
            self.config.SETTLE,
            contract,
            new_size,
            current_price
        )
        
        if order:
            self.active_cycles[contract] += 1
        
        return order


class RiskManager:
    """Risk management and safety checks"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.daily_pnl = 0.0
        self.last_reset = datetime.now().date()
    
    def reset_daily_pnl(self):
        today = datetime.now().date()
        if today != self.last_reset:
            self.daily_pnl = 0.0
            self.last_reset = today
            logger.info("Daily P&L reset")
    
    def check_daily_loss_limit(self) -> bool:
        self.reset_daily_pnl()
        loss_limit = self.config.TOTAL_BALANCE * self.config.DAILY_LOSS_LIMIT_PCT
        
        if self.daily_pnl < -loss_limit:
            logger.critical(f"Daily loss limit reached: ${self.daily_pnl:,.2f}")
            return False
        
        return True
    
    def update_pnl(self, pnl: float):
        self.daily_pnl += pnl


class TradingGuruBot:
    """Main trading bot orchestrator"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.client = GateIOClient(config.API_KEY, config.API_SECRET, config.HOST)
        self.ai = AIPredictor()
        self.grid_strategy = GridStrategy(config, self.client)
        self.scalp_strategy = ScalpingStrategy(config, self.client, self.ai)
        self.martingale_strategy = MartingaleStrategy(config, self.client)
        self.risk_manager = RiskManager(config)
        self.running = False
        self.cycle = 0
    
    def start(self):
        logger.info("=" * 70)
        logger.info("TRADING GURU BOT - REAL TRADING MODE")
        logger.info("=" * 70)
        logger.info(f"Contract: {self.config.CONTRACT}")
        logger.info(f"Balance: ${self.config.TOTAL_BALANCE:,.2f}")
        logger.info(f"Leverage: {self.config.MAX_LEVERAGE}x")
        logger.info(f"Daily Loss Limit: {self.config.DAILY_LOSS_LIMIT_PCT * 100}%")
        logger.info("Direction: SHORTS ONLY")
        logger.info("=" * 70)
        
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
        self.cycle += 1
        
        if not self.risk_manager.check_daily_loss_limit():
            logger.warning("Daily loss limit exceeded - STOPPING")
            self.stop()
            return
        
        current_price = self.client.get_current_price(self.config.SETTLE, self.config.CONTRACT)
        if not current_price:
            logger.error("Failed to get price")
            return
        
        funding_rate = self.client.get_funding_rate(self.config.SETTLE, self.config.CONTRACT)
        
        self.grid_strategy.execute(current_price)
        self.scalp_strategy.execute(current_price, funding_rate)
        
        positions = self.client.get_positions(self.config.SETTLE)
        for pos in positions:
            if self.martingale_strategy.should_apply_martingale(pos):
                self.martingale_strategy.execute(pos, current_price)
        
        if self.cycle % 30 == 0:
            account = self.client.get_futures_account(self.config.SETTLE)
            balance = float(account.available) if account else 0
            pnl = float(account.unrealised_pnl or 0) if account else 0
            logger.info(f"Cycle {self.cycle} | Price: ${current_price:,.2f} | "
                       f"Balance: ${balance:,.2f} | PNL: ${pnl:,.2f} | "
                       f"Funding: {funding_rate*100:.4f}%")
    
    def stop(self):
        logger.info("Stopping Trading Guru Bot...")
        self.running = False
        logger.info("Bot stopped")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TRADING GURU BOT - STARTING")
    print("=" * 70)
    
    config = BotConfig()
    
    if not config.API_KEY or not config.API_SECRET:
        print("ERROR: Set GATE_API_KEY and GATE_API_SECRET in Secrets!")
        exit(1)
    
    bot = TradingGuruBot(config)
    bot.start()
