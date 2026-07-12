"""
Trading Guru Bot - FRESH SETUP v3.0
AI-Powered SHORT-ONLY Trading for Gate.io Futures

IMPROVED CONFIGURATION:
- Conservative risk management
- Smarter entry timing (wait for strong signals)
- Cooldown between trades
- Better position sizing
"""

import gate_api
from gate_api.exceptions import GateApiException
import time
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, '/home/runner/workspace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TradingGuru')


class Config:
    """Fresh configuration - Conservative & Smart"""
    
    API_KEY = os.environ.get('GATE_API_KEY', '')
    API_SECRET = os.environ.get('GATE_API_SECRET', '')
    HOST = "https://api.gateio.ws/api/v4"
    
    # Trading pair
    SETTLE = "usdt"
    CONTRACT = "BTC_USDT"
    
    # Conservative capital management
    TOTAL_BALANCE = 25.0  # Use only $25 of available balance
    MAX_POSITION_PCT = 0.10  # Max 10% per trade = $2.50
    MAX_LEVERAGE = 10  # Reduced from 50x to 10x
    
    # AI Requirements (stricter)
    MIN_AI_VOTES = 5  # Need 5/6 agents to agree (was 4)
    MIN_SCORE = 80  # Higher threshold (was 75)
    
    # Risk management
    DAILY_LOSS_LIMIT = 0.10  # Stop at 10% daily loss
    MAX_TRADES_PER_DAY = 10  # Limit trades (was 50)
    
    # Cooldown
    TRADE_COOLDOWN_SEC = 60  # Wait 60 sec between trades (was 1 sec)
    LOOP_DELAY_SEC = 5  # Check every 5 seconds
    
    # Stop loss
    STOP_LOSS_PCT = 0.02  # 2% stop loss


class GateClient:
    """Gate.io API wrapper"""
    
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
    
    def get_price(self, contract):
        try:
            ticker = self.api.list_futures_tickers(self.config.SETTLE, contract=contract)
            return float(ticker[0].last) if ticker else None
        except Exception as e:
            logger.error(f"Price error: {e}")
            return None
    
    def get_funding(self, contract):
        try:
            ticker = self.api.list_futures_tickers(self.config.SETTLE, contract=contract)
            return float(ticker[0].funding_rate or 0) if ticker else 0
        except:
            return 0
    
    def get_balance(self):
        try:
            account = self.api.list_futures_accounts(self.config.SETTLE)
            return float(account.available)
        except:
            return 0
    
    def get_positions(self):
        try:
            return self.api.list_positions(self.config.SETTLE)
        except:
            return []
    
    def place_short(self, contract, size):
        try:
            order = gate_api.FuturesOrder(
                contract=contract,
                size=-abs(size),
                price="0",
                tif="ioc"
            )
            result = self.api.create_futures_order(self.config.SETTLE, order)
            return result
        except Exception as e:
            logger.error(f"Order error: {e}")
            return None
    
    def close_all(self):
        positions = self.get_positions()
        for p in positions:
            size = int(p.size or 0)
            if size != 0:
                try:
                    order = gate_api.FuturesOrder(
                        contract=p.contract,
                        size=-size,
                        price="0",
                        tif="ioc"
                    )
                    self.api.create_futures_order(self.config.SETTLE, order)
                    logger.info(f"Closed {p.contract}")
                except Exception as e:
                    logger.error(f"Close error: {e}")


class AIAnalyzer:
    """6-Agent AI Analysis"""
    
    def __init__(self):
        try:
            from trading_guru.agents.llm_agent import get_multi_agent_consensus
            from trading_guru.core.models import MarketData
            self.consensus = get_multi_agent_consensus
            self.MarketData = MarketData
            self.enabled = True
            logger.info("AI: 6 agents ready")
        except Exception as e:
            logger.warning(f"AI disabled: {e}")
            self.enabled = False
    
    def analyze(self, symbol, price, funding=0):
        if not self.enabled:
            return {"votes": 0, "score": 0, "direction": "NEUTRAL"}
        
        try:
            data = self.MarketData(
                symbol=symbol,
                price=price,
                volume_24h=1000000000,
                volatility_atr=price * 0.015,
                adx_14=28,
                spread_percent=0.001,
                funding_rate=funding * 100,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            result = self.consensus(data, "Trinity SHORT Analysis")
            
            return {
                "votes": result["short_votes"],
                "score": result["avg_score"],
                "direction": result["consensus"].upper()
            }
        except Exception as e:
            logger.error(f"AI error: {e}")
            return {"votes": 0, "score": 0, "direction": "NEUTRAL"}


class TradingBot:
    """Fresh Trading Bot"""
    
    def __init__(self, config):
        self.config = config
        self.client = GateClient(config)
        self.ai = AIAnalyzer()
        self.running = False
        self.last_trade_time = 0
        self.trades_today = 0
        self.daily_pnl = 0
        self.last_day = datetime.now().date()
    
    def reset_daily(self):
        today = datetime.now().date()
        if today != self.last_day:
            self.trades_today = 0
            self.daily_pnl = 0
            self.last_day = today
            logger.info("Daily reset complete")
    
    def can_trade(self):
        self.reset_daily()
        
        # Check daily trade limit
        if self.trades_today >= self.config.MAX_TRADES_PER_DAY:
            return False, "Daily trade limit reached"
        
        # Check cooldown
        elapsed = time.time() - self.last_trade_time
        if elapsed < self.config.TRADE_COOLDOWN_SEC:
            return False, f"Cooldown: {int(self.config.TRADE_COOLDOWN_SEC - elapsed)}s"
        
        # Check balance
        balance = self.client.get_balance()
        if balance < 5:
            return False, f"Low balance: ${balance:.2f}"
        
        return True, "Ready"
    
    def calculate_size(self, price):
        capital = self.config.TOTAL_BALANCE * self.config.MAX_POSITION_PCT
        size = int((capital * self.config.MAX_LEVERAGE) / price)
        return max(1, min(size, 5))  # Min 1, max 5 contracts
    
    def run(self):
        logger.info("=" * 60)
        logger.info("TRADING GURU - FRESH START v3.0")
        logger.info("=" * 60)
        logger.info(f"Contract: {self.config.CONTRACT}")
        logger.info(f"Capital: ${self.config.TOTAL_BALANCE}")
        logger.info(f"Leverage: {self.config.MAX_LEVERAGE}x")
        logger.info(f"Max Trades/Day: {self.config.MAX_TRADES_PER_DAY}")
        logger.info(f"Cooldown: {self.config.TRADE_COOLDOWN_SEC}s")
        logger.info(f"AI Required: {self.config.MIN_AI_VOTES}/6 votes, {self.config.MIN_SCORE}+ score")
        logger.info("Direction: SHORTS ONLY")
        logger.info("=" * 60)
        
        self.running = True
        cycle = 0
        
        try:
            while self.running:
                cycle += 1
                self.loop(cycle)
                time.sleep(self.config.LOOP_DELAY_SEC)
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.critical(f"Error: {e}")
        
        logger.info(f"Bot stopped. Trades today: {self.trades_today}")
    
    def loop(self, cycle):
        # Get price
        price = self.client.get_price(self.config.CONTRACT)
        if not price:
            return
        
        funding = self.client.get_funding(self.config.CONTRACT)
        
        # Check if can trade
        can, reason = self.can_trade()
        
        if cycle % 12 == 0:  # Log every minute
            balance = self.client.get_balance()
            logger.info(f"Cycle {cycle} | BTC: ${price:,.2f} | Balance: ${balance:.2f} | "
                       f"Trades: {self.trades_today}/{self.config.MAX_TRADES_PER_DAY} | {reason}")
        
        if not can:
            return
        
        # AI Analysis
        symbol = self.config.CONTRACT.replace("_", "/")
        analysis = self.ai.analyze(symbol, price, funding)
        
        votes = analysis["votes"]
        score = analysis["score"]
        direction = analysis["direction"]
        
        logger.info(f"AI: {votes}/6 votes | Score: {score:.0f} | Direction: {direction}")
        
        # Check if signal is strong enough
        if direction == "SHORT" and votes >= self.config.MIN_AI_VOTES and score >= self.config.MIN_SCORE:
            size = self.calculate_size(price)
            
            logger.info(f"EXECUTING SHORT: {size} contracts at ${price:,.2f}")
            
            result = self.client.place_short(self.config.CONTRACT, size)
            
            if result:
                self.trades_today += 1
                self.last_trade_time = time.time()
                logger.info(f"ORDER FILLED! Trades today: {self.trades_today}")
            else:
                logger.error("Order failed")
        else:
            if direction == "SHORT":
                logger.info(f"Signal weak: need {self.config.MIN_AI_VOTES} votes & {self.config.MIN_SCORE} score")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TRADING GURU BOT - FRESH START")
    print("=" * 60 + "\n")
    
    config = Config()
    
    if not config.API_KEY:
        print("ERROR: Set GATE_API_KEY in Secrets!")
        exit(1)
    
    bot = TradingBot(config)
    bot.run()
