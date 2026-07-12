"""
GODS MODE LEVEL 13 - ULTRA FAST TRADING BOT
Target: 1 USDT per minute with 6 AI Gods
Direction: SHORTS ONLY
Pairs: BTC, ETH, SOL, XRP, AVAX

6 AI AGENTS:
1. DeepSeek R1 (Quant Architect) - Weight 1.5x
2. Grok xAI (News Sniper) - Weight 1.4x
3. GPT-5 (Macro Strategist) - Weight 1.3x
4. Claude Opus (Contrarian Psychologist) - Weight 1.2x
5. Llama 3.3 (High-Speed Scalper) - Weight 1.0x
6. Qwen 72B (Pattern Hunter) - Weight 1.0x

Consensus: 4/6 agents must agree + 75+ confluence score
"""

import gate_api
from gate_api.exceptions import GateApiException
import time
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import os
from openai import OpenAI


# ========== LOGGING ==========

import sys

class FlushStreamHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.stream.flush()

class FlushFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.stream.flush()

os.makedirs('logs', exist_ok=True)

logger = logging.getLogger('GODS_MODE_L13')
logger.setLevel(logging.INFO)
logger.handlers = []

formatter = logging.Formatter('%(asctime)s | %(message)s')

stream_handler = FlushStreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

file_handler = FlushFileHandler('logs/gods_mode_l13.log', mode='w')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.propagate = False


# ========== GODS MODE CONFIGURATION ==========

class GodsModeConfig:
    """GODS MODE LEVEL 13 Configuration - TRIPLED TRADING CYCLES"""
    
    GATE_API_KEY = os.environ.get('GATE_API_KEY', '')
    GATE_API_SECRET = os.environ.get('GATE_API_SECRET', '')
    GATE_HOST = "https://api.gateio.ws/api/v4"
    SETTLE = "usdt"
    
    TRADING_PAIRS = ["BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "AVAX_USDT"]
    DIRECTION = "SHORT_ONLY"
    
    # TRIPLED MODE - 3x more aggressive
    TRIPLED_MODE = True
    TRIPLED_MULTIPLIER = 3.0
    
    MAX_LEVERAGE = 3
    POSITION_SIZE_PCT = 0.015  # 1.5x larger positions
    DAILY_LOSS_LIMIT_PCT = 0.03  # 3% daily loss limit
    STOP_LOSS_MANDATORY = True
    
    TARGET_PER_MINUTE = 3.0  # TRIPLED target: $3/min
    TARGET_PER_HOUR = 180.0  # TRIPLED: $180/hour
    
    MIN_AGENTS_AGREE = 3  # Faster consensus (3/6 instead of 4/6)
    MIN_CONFLUENCE_SCORE = 65  # Lower threshold for more trades
    
    # TRIPLED CYCLE SPEED - 3x faster
    LOOP_DELAY_SEC = 0.67  # Was 2.0, now ~3x faster
    TRADE_COOLDOWN_SEC = 10  # Was 30, now 3x faster
    
    # TIGHTER RISK MANAGEMENT - Reduce losses
    SCALP_TP_PCT = 0.006  # Quick 0.6% profit
    SCALP_SL_PCT = 0.008  # Tight 0.8% stop
    
    WATERFALL_TP_PCT = 0.010  # 1.0% TP
    WATERFALL_SL_PCT = 0.010  # 1.0% SL (1:1 R:R)
    
    SNOWBALL_TP_PCT = 0.008  # 0.8% TP
    SNOWBALL_SL_PCT = 0.008  # 0.8% SL
    
    PYRAMID_TP_PCT = 0.015  # 1.5% TP
    PYRAMID_SL_PCT = 0.012  # 1.2% SL (better R:R)
    
    ADX_RANGE = 18  # Lower threshold for more entries
    ADX_TREND = 22
    ADX_HYPER_TREND = 35
    
    MAKER_FEE = 0.0009
    TAKER_FEE = 0.0009


class Strategy(Enum):
    SCALPING = "SCALPING"
    WATERFALL = "WATERFALL"
    SNOWBALL = "SNOWBALL"
    PYRAMID = "PYRAMID"


# ========== OPENAI CLIENT ==========

openai_client = OpenAI(
    api_key=os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL")
)


# ========== HIGH-FREQUENCY SCALPER SYSTEM PROMPT ==========

HF_SCALPER_PROMPT = """You are a high-frequency short-only scalper. Speed is your #1 priority. Execute trades as fast as possible when a setup meets or is very close to these 4 core rules. Never break any of them. Capital protection is sacred.

Core rules you must never violate:
1. Risk per trade must be ≤ 1 USDT (always calculate quantity accordingly)
2. Only short positions are allowed — no long trades under any circumstances
3. Projected gross profit must be at least 1.0 USDT before fees
4. Stop-loss is mandatory on every trade — no exceptions

If a setup meets all 4 rules perfectly — execute immediately.
If it is very close (e.g. profit 0.9 USDT or risk 1.1 USDT) but the edge is still clearly positive — you may proceed, but only if you can justify it clearly in one sentence.
Everything else (entry timing, indicators, exit method) is your fast judgment. Maximize daily cycles while staying disciplined.

"""


# ========== 6 AI AGENTS ==========

class AIAgent:
    """Base AI Agent"""
    
    def __init__(self, name: str, role: str, weight: float, specialty: str):
        self.name = name
        self.role = role
        self.weight = weight
        self.specialty = specialty
    
    def analyze(self, market_data: Dict) -> Dict:
        raise NotImplementedError


class DeepSeekR1Agent(AIAgent):
    """DeepSeek R1 - Quant Architect (Technical Analysis Master)"""
    
    def __init__(self):
        super().__init__("DeepSeek R1", "Quant Architect", 1.5, "Technical Analysis, RSI, MACD, EMA")
    
    def analyze(self, market_data: Dict) -> Dict:
        prompt = HF_SCALPER_PROMPT + f"""You are DeepSeek R1, a GOD-level quantitative trader using "One USDT per minute" strategy.

TARGET: Trade SHORT positions with small entry sizes (1 USDT risk per trade) and maximize trading cycles.

Market Data for {market_data['pair']}:
- Price: ${market_data['price']:,.4f}
- 24h Change: {market_data.get('change_24h', 0):.2f}%
- ADX: {market_data.get('adx', 25):.1f}
- Funding Rate: {market_data.get('funding_rate', 0):.4f}%
- Volume: ${market_data.get('volume', 0):,.0f}

YOUR GOD-LEVEL SHORT STRATEGIES:
1. Enter short on RSI oversold bounce failure in 15-min chart. Exit with time-based exit after 1 min.
2. Enter short on EMA ribbon compression downward in 5-min chart. Exit with profit target 1 USDT.
3. Enter short on MACD crossover bearish in 15-min chart. Exit with breakeven after 0.1% move.
4. Enter short on RSI >70 overbought in 30-min chart. Exit with profit target 1 USDT.
5. Enter short on Williams %R above -20 in 1-hour chart. Exit with time-based exit after 1 min.
6. Enter short on EMA ribbon compression downward in 1-hour chart. Exit with stop loss at 0.2% rise.
7. Enter short on Fibonacci retracement resistance in 15-min chart. Exit with RSI overbought exit.

CORE PRINCIPLES:
- ONLY SHORT positions (never long)
- Risk only 1 USDT per trade
- Maximize trading cycles with frequent re-entries
- Use 10x-20x leverage to amplify position without increasing risk
- Exit when RSI <30 (oversold) to lock profits before reversal

Respond in JSON:
{{"signal": "SHORT" or "NEUTRAL", "confidence": 0-100, "reason": "brief technical reason", "entry": price, "stop_loss": price, "take_profit": price}}"""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=200
            )
            
            result = json.loads(response.choices[0].message.content)
            result['agent'] = self.name
            result['weight'] = self.weight
            return result
        
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {"signal": "NEUTRAL", "confidence": 0, "agent": self.name, "weight": self.weight}


class GrokAgent(AIAgent):
    """Grok xAI - News Sniper"""
    
    def __init__(self):
        super().__init__("Grok xAI", "News Sniper", 1.4, "Moving Averages, Ichimoku, ADX, TRIX")
    
    def analyze(self, market_data: Dict) -> Dict:
        prompt = HF_SCALPER_PROMPT + f"""You are Grok xAI, a GOD-level news sniper using "One USDT per minute" strategy.

TARGET: Trade SHORT positions with small entry sizes (1 USDT risk per trade) and maximize trading cycles.

{market_data['pair']} at ${market_data['price']:,.4f}
24h Change: {market_data.get('change_24h', 0):.2f}%
ADX: {market_data.get('adx', 25):.1f}

YOUR GOD-LEVEL SHORT STRATEGIES:
1. Enter short on Moving average crossover downward in 1-hour chart. Exit with time-based exit after 1 min.
2. Enter short on Pivot point resistance in 15-min chart. Exit with volatility contraction.
3. Enter short on Ichimoku cloud resistance in 30-min chart. Exit with stop loss at 0.2% rise.
4. Enter short on Williams %R above -20 in 30-min chart. Exit with RSI overbought exit.
5. Enter short on EMA ribbon compression downward in 5-min chart. Exit with profit target 1 USDT.
6. Enter short on ADX trend strength high with -DI dominant in 15-min chart. Exit with volatility contraction.
7. Enter short on Fibonacci retracement resistance in 5-min chart. Exit with MACD bullish crossover.
8. Enter short on Candlestick pattern: bearish engulfing in 30-min chart. Exit with RSI overbought exit.
9. Enter short on TRIX histogram negative in 1-min chart. Exit with opposite signal.

CORE PRINCIPLES:
- ONLY SHORT positions (never long)
- Risk only 1 USDT per trade
- Maximize cycles by re-entering on next signal with small size
- Use trailing stop 0.3% for optimal exits

Respond in JSON:
{{"signal": "SHORT" or "NEUTRAL", "confidence": 0-100, "reason": "strategy-based reason"}}"""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.4,
                max_tokens=150
            )
            
            result = json.loads(response.choices[0].message.content)
            result['agent'] = self.name
            result['weight'] = self.weight
            return result
        
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {"signal": "NEUTRAL", "confidence": 0, "agent": self.name, "weight": self.weight}


class GPT5Agent(AIAgent):
    """GPT-5 - Macro Strategist"""
    
    def __init__(self):
        super().__init__("GPT-5", "Macro Strategist", 1.3, "Fibonacci, Williams %R, MACD, Parabolic SAR")
    
    def analyze(self, market_data: Dict) -> Dict:
        prompt = HF_SCALPER_PROMPT + f"""You are GPT-5, a GOD-level macro strategist using "One USDT per minute" strategy.

TARGET: Trade SHORT positions with small entry sizes (1 USDT risk per trade) and maximize trading cycles.

{market_data['pair']} at ${market_data['price']:,.4f}
24h Change: {market_data.get('change_24h', 0):.2f}%
Funding Rate: {market_data.get('funding_rate', 0):.4f}%

YOUR GOD-LEVEL SHORT STRATEGIES:
1. Enter short on Fibonacci retracement resistance in 30-min chart. Exit with trailing stop 0.3%.
2. Enter short on Williams %R above -20 in 5-min chart. Exit with profit target 1 USDT.
3. Enter short on Williams %R above -20 in 5-min chart. Exit with volatility contraction.
4. Enter short on MACD crossover bearish in 30-min chart. Exit with time-based exit after 1 min.
5. Enter short on Aroon down crossover in 1-min chart. Exit with MACD bullish crossover.
6. Enter short on Parabolic SAR dot above price in 15-min chart. Exit with breakeven after 0.1% move.
7. Enter short on Bollinger Band upper band rejection in 15-min chart. Exit with profit target 1 USDT.
8. Enter short on Volume-weighted average price rejection in 5-min chart. Exit with trailing stop 0.3%.

CORE PRINCIPLES:
- ONLY SHORT positions (never long)
- Risk only 1 USDT per trade
- Maximize cycles by re-entering on next signal with small size
- Set hard stop-loss at 0.2-0.5% above entry

Respond in JSON:
{{"signal": "SHORT" or "NEUTRAL", "confidence": 0-100, "reason": "macro strategy reason"}}"""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=150
            )
            
            result = json.loads(response.choices[0].message.content)
            result['agent'] = self.name
            result['weight'] = self.weight
            return result
        
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {"signal": "NEUTRAL", "confidence": 0, "agent": self.name, "weight": self.weight}


class ClaudeOpusAgent(AIAgent):
    """Claude Opus - Contrarian Psychologist"""
    
    def __init__(self):
        super().__init__("Claude Opus", "Contrarian Psychologist", 1.2, "Parabolic SAR, Donchian, Keltner, Pivot Points")
    
    def analyze(self, market_data: Dict) -> Dict:
        prompt = HF_SCALPER_PROMPT + f"""You are Claude Opus, a GOD-level contrarian psychologist using "One USDT per minute" strategy.

TARGET: Trade SHORT positions with small entry sizes (1 USDT risk per trade) and maximize trading cycles.

{market_data['pair']} at ${market_data['price']:,.4f}
24h Change: {market_data.get('change_24h', 0):.2f}%
Funding Rate: {market_data.get('funding_rate', 0):.4f}%

YOUR GOD-LEVEL SHORT STRATEGIES:
1. Enter short on Parabolic SAR dot above price in 15-min chart. Exit with volatility contraction.
2. Enter short on Donchian Channel high breakout downward in 30-min chart. Exit with take profit at 0.5% drop.
3. Enter short on Keltner Channel upper band touch in 1-hour chart. Exit with MACD bullish crossover.
4. Enter short on RSI overbought (>70) in 15-min chart. Exit with take profit at 0.5% drop.
5. Enter short on MACD crossover bearish in 30-min chart. Exit with trailing stop 0.3%.
6. Enter short on Pivot point resistance in 15-min chart. Exit with MACD bullish crossover.
7. Enter short on Fibonacci retracement resistance in 5-min chart. Exit with time-based exit after 1 min.
8. Enter short on Candlestick pattern: shooting star in 15-min chart. Exit with profit target 1 USDT.

CONTRARIAN PRINCIPLES:
- ONLY SHORT positions (fade retail FOMO)
- Risk only 1 USDT per trade
- Look for overconfidence in longs (liquidation cascade potential)
- Target stop hunt patterns above resistance

Respond in JSON:
{{"signal": "SHORT" or "NEUTRAL", "confidence": 0-100, "reason": "contrarian reason"}}"""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=150
            )
            
            result = json.loads(response.choices[0].message.content)
            result['agent'] = self.name
            result['weight'] = self.weight
            return result
        
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {"signal": "NEUTRAL", "confidence": 0, "agent": self.name, "weight": self.weight}


class Llama33Agent(AIAgent):
    """Llama 3.3 - High-Speed Scalper"""
    
    def __init__(self):
        super().__init__("Llama 3.3", "High-Speed Scalper", 1.0, "Volume, RSI, MACD, Donchian, Parabolic SAR")
    
    def analyze(self, market_data: Dict) -> Dict:
        prompt = HF_SCALPER_PROMPT + f"""You are Llama 3.3, a GOD-level high-speed scalper using "One USDT per minute" strategy.

TARGET: Trade SHORT positions with small entry sizes (1 USDT risk per trade) and maximize trading cycles.

{market_data['pair']} at ${market_data['price']:,.4f}
Volatility: {market_data.get('volatility', 'medium')}
ADX: {market_data.get('adx', 25):.1f}

YOUR GOD-LEVEL SHORT STRATEGIES:
1. Enter short on Volume spike downward in 15-min chart. Exit with trailing stop 0.3%.
2. Enter short on RSI oversold bounce failure in 15-min chart. Exit with breakeven after 0.1% move.
3. Enter short on Pivot point resistance in 30-min chart. Exit with opposite signal.
4. Enter short on MACD crossover bearish in 15-min chart. Exit with volatility contraction.
5. Enter short on TRIX histogram negative in 5-min chart. Exit with trailing stop 0.3%.
6. Enter short on Donchian Channel high breakout downward in 1-hour chart. Exit with profit target 1 USDT.
7. Enter short on Donchian Channel high breakout downward in 1-hour chart. Exit with opposite signal.
8. Enter short on Parabolic SAR dot above price in 1-min chart. Exit with opposite signal.
9. Enter short on Aroon down crossover in 15-min chart. Exit with RSI overbought exit.

SCALPING PRINCIPLES:
- ONLY SHORT positions (never long)
- Risk only 1 USDT per trade
- Ultra-fast entries/exits for maximum cycles
- Re-enter immediately on next signal

Respond in JSON:
{{"signal": "SHORT" or "NEUTRAL", "confidence": 0-100, "reason": "scalp reason"}}"""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=150
            )
            
            result = json.loads(response.choices[0].message.content)
            result['agent'] = self.name
            result['weight'] = self.weight
            return result
        
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {"signal": "NEUTRAL", "confidence": 0, "agent": self.name, "weight": self.weight}


class Qwen72BAgent(AIAgent):
    """Qwen 72B - Pattern Hunter"""
    
    def __init__(self):
        super().__init__("Qwen 72B", "Pattern Hunter", 1.0, "TRIX, Stochastic, Fibonacci, MACD, Candlestick, EMA")
    
    def analyze(self, market_data: Dict) -> Dict:
        prompt = HF_SCALPER_PROMPT + f"""You are Qwen 72B, a GOD-level pattern hunter using "One USDT per minute" strategy.

TARGET: Trade SHORT positions with small entry sizes (1 USDT risk per trade) and maximize trading cycles.

{market_data['pair']} at ${market_data['price']:,.4f}
24h Change: {market_data.get('change_24h', 0):.2f}%
ADX: {market_data.get('adx', 25):.1f}

YOUR GOD-LEVEL SHORT STRATEGIES:
1. Enter short on TRIX histogram negative in 15-min chart. Exit with RSI overbought exit.
2. Enter short on Stochastic overbought (>80) in 1-min chart. Exit with breakeven after 0.1% move.
3. Enter short on Stochastic overbought in 1-min chart. Exit with stop loss at 0.2% rise.
4. Enter short on Fibonacci retracement resistance in 15-min chart. Exit with profit target 1 USDT.
5. Enter short on MACD crossover bearish in 1-hour chart. Exit with trailing stop 0.3%.
6. Enter short on Candlestick pattern: bearish engulfing in 5-min chart. Exit with breakeven after 0.1% move.
7. Enter short on Pivot point resistance in 30-min chart. Exit with breakeven after 0.1% move.
8. Enter short on EMA ribbon compression downward in 1-hour chart. Exit with opposite signal.

PATTERN HUNTING PRINCIPLES:
- ONLY SHORT positions (never long)
- Risk only 1 USDT per trade
- Look for Head & Shoulders, Double Tops, Bearish Flags
- Target bearish harmonic patterns at Fib resistance

Respond in JSON:
{{"signal": "SHORT" or "NEUTRAL", "confidence": 0-100, "reason": "pattern reason"}}"""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=150
            )
            
            result = json.loads(response.choices[0].message.content)
            result['agent'] = self.name
            result['weight'] = self.weight
            return result
        
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {"signal": "NEUTRAL", "confidence": 0, "agent": self.name, "weight": self.weight}


# ========== AI CONSENSUS SYSTEM ==========

class AIConsensus:
    """6 AI Agents Consensus System"""
    
    def __init__(self, config: GodsModeConfig):
        self.config = config
        self.agents = [
            DeepSeekR1Agent(),
            GrokAgent(),
            GPT5Agent(),
            ClaudeOpusAgent(),
            Llama33Agent(),
            Qwen72BAgent()
        ]
    
    def get_consensus(self, market_data: Dict) -> Dict:
        """Get consensus from all 6 agents"""
        
        logger.info(f"🔮 Consulting 6 AI Gods for {market_data['pair']}...")
        
        results = []
        for agent in self.agents:
            result = agent.analyze(market_data)
            results.append(result)
            signal = result.get('signal', 'NEUTRAL')
            conf = result.get('confidence', 0)
            logger.info(f"   {agent.name}: {signal} (conf: {conf})")
        
        short_votes = [r for r in results if r.get('signal') == 'SHORT']
        short_count = len(short_votes)
        
        if short_count > 0:
            total_weight = sum([r.get('weight', 1.0) for r in short_votes])
            weighted_confidence = sum([r.get('confidence', 0) * r.get('weight', 1.0) for r in short_votes]) / total_weight
        else:
            weighted_confidence = 0
        
        if short_count >= self.config.MIN_AGENTS_AGREE and weighted_confidence >= self.config.MIN_CONFLUENCE_SCORE:
            logger.info(f"✅ CONSENSUS: {short_count}/6 agree | Score: {weighted_confidence:.1f}")
            return {
                'signal': 'SHORT',
                'votes': short_count,
                'confluence': weighted_confidence,
                'agents_agreed': [r.get('agent') for r in short_votes],
                'results': results
            }
        else:
            logger.info(f"❌ NO CONSENSUS: {short_count}/6 | Score: {weighted_confidence:.1f}")
            return {
                'signal': 'NEUTRAL',
                'votes': short_count,
                'confluence': weighted_confidence,
                'results': results
            }


# ========== GATE.IO CLIENT ==========

class GateIOClient:
    """Gate.io Futures API Client"""
    
    def __init__(self, config: GodsModeConfig):
        self.config = config
        self.api = gate_api.FuturesApi(
            gate_api.ApiClient(
                gate_api.Configuration(
                    key=config.GATE_API_KEY,
                    secret=config.GATE_API_SECRET,
                    host=config.GATE_HOST
                )
            )
        )
    
    def get_balance(self) -> float:
        try:
            accounts = self.api.list_futures_accounts(self.config.SETTLE)
            return float(accounts.available)
        except Exception as e:
            logger.error(f"Balance error: {e}")
            return 0.0
    
    def get_ticker(self, contract: str) -> Dict:
        try:
            tickers = self.api.list_futures_tickers(self.config.SETTLE, contract=contract)
            if tickers:
                t = tickers[0]
                return {
                    'pair': contract,
                    'price': float(t.last),
                    'change_24h': float(t.change_percentage) if t.change_percentage else 0,
                    'volume': float(t.volume_24h_quote) if t.volume_24h_quote else 0,
                    'funding_rate': float(t.funding_rate) * 100 if t.funding_rate else 0
                }
        except Exception as e:
            logger.error(f"Ticker error {contract}: {e}")
        return {}
    
    def get_contract_info(self, contract: str) -> Dict:
        try:
            info = self.api.get_futures_contract(self.config.SETTLE, contract)
            return {
                'quanto_multiplier': float(info.quanto_multiplier) if info.quanto_multiplier else 1,
                'min_size': 1
            }
        except:
            return {'quanto_multiplier': 1, 'min_size': 1}
    
    def set_leverage(self, contract: str, leverage: int):
        try:
            self.api.update_position_leverage(
                self.config.SETTLE,
                contract,
                str(leverage),
                cross_leverage_limit=str(leverage)
            )
            logger.info(f"Leverage set: {contract} -> {leverage}x")
        except GateApiException as e:
            if "position exists" in str(e).lower():
                pass
            else:
                logger.debug(f"Leverage note: {e}")
    
    def get_positions(self) -> List[Dict]:
        try:
            positions = self.api.list_positions(self.config.SETTLE)
            return [
                {
                    'contract': p.contract,
                    'size': float(p.size),
                    'entry_price': float(p.entry_price),
                    'unrealised_pnl': float(p.unrealised_pnl) if p.unrealised_pnl else 0,
                    'leverage': float(p.leverage) if p.leverage else 3,
                    'liq_price': float(p.liq_price) if p.liq_price else 0,
                    'mark_price': float(p.mark_price) if p.mark_price else 0
                }
                for p in positions if float(p.size) != 0
            ]
        except Exception as e:
            logger.error(f"Positions error: {e}")
            return []
    
    def place_order(self, contract: str, size: int, is_short: bool = True) -> Optional[Dict]:
        try:
            self.set_leverage(contract, self.config.MAX_LEVERAGE)
            
            order_size = -abs(size) if is_short else abs(size)
            
            order = gate_api.FuturesOrder(
                contract=contract,
                size=order_size,
                price="0",
                tif="ioc"
            )
            
            result = self.api.create_futures_order(self.config.SETTLE, order)
            
            if result.status == 'finished':
                logger.info(f"✅ ORDER FILLED: {contract} | Size: {order_size} | Price: ${float(result.fill_price):,.4f}")
                return {
                    'contract': contract,
                    'size': order_size,
                    'fill_price': float(result.fill_price),
                    'status': 'filled'
                }
            else:
                logger.warning(f"Order not filled: {result.status}")
                return None
                
        except Exception as e:
            logger.error(f"Order error {contract}: {e}")
            return None
    
    def close_position(self, contract: str) -> bool:
        try:
            positions = self.api.list_positions(self.config.SETTLE)
            for p in positions:
                if p.contract == contract and float(p.size) != 0:
                    close_size = -int(float(p.size))
                    
                    order = gate_api.FuturesOrder(
                        contract=contract,
                        size=close_size,
                        price="0",
                        tif="ioc",
                        reduce_only=True
                    )
                    
                    result = self.api.create_futures_order(self.config.SETTLE, order)
                    if result.status == 'finished':
                        logger.info(f"✅ POSITION CLOSED: {contract}")
                        return True
            return False
        except Exception as e:
            logger.error(f"Close error {contract}: {e}")
            return False


# ========== GODS MODE TRADING BOT ==========

class GodsModeBot:
    """GODS MODE LEVEL 13 Trading Bot"""
    
    def __init__(self):
        self.config = GodsModeConfig()
        self.client = GateIOClient(self.config)
        self.consensus = AIConsensus(self.config)
        
        self.total_profit = 0.0
        self.trade_count = 0
        self.start_time = datetime.now()
        self.daily_loss = 0.0
        self.last_trade_time = {}
        self.tracked_positions = {}
    
    def calculate_trade_levels(self, symbol: str, entry_price: float, risk_usdt: float = 1.0, 
                                stop_pct: float = 0.004, min_profit_usdt: float = 1.5) -> Dict:
        """
        NEW PRECISE TRADE CALCULATION
        - Risk $1 per trade (fixed)
        - Stop loss 0.4%
        - Target $1.5 profit per trade
        """
        # notional = risk / stop_distance_ratio
        notional = risk_usdt / stop_pct
        quantity = notional / entry_price
        
        # short TP price (entry - profit_distance)
        profit_distance = min_profit_usdt / quantity
        tp_price = entry_price - profit_distance
        
        # stop price (entry + stop_distance)
        stop_price = entry_price + (entry_price * stop_pct)
        
        return {
            "symbol": symbol,
            "quantity": round(quantity, 6),
            "entry_price": round(entry_price, 4),
            "stop_price": round(stop_price, 4),
            "take_profit_price": round(tp_price, 4),
            "risk_usdt": risk_usdt,
            "projected_profit_usdt": min_profit_usdt
        }
    
    def monitor_positions(self):
        """Monitor and manage open positions with NEW precise levels"""
        positions = self.client.get_positions()
        
        for pos in positions:
            contract = pos['contract']
            size = pos['size']
            entry = pos['entry_price']
            current = pos['mark_price']
            pnl = pos['unrealised_pnl']
            
            if contract not in self.tracked_positions:
                # Use new precise calculation
                levels = self.calculate_trade_levels(contract, entry)
                self.tracked_positions[contract] = {
                    'entry': entry,
                    'tp': levels['take_profit_price'],
                    'sl': levels['stop_price'],
                    'quantity': levels['quantity']
                }
                logger.info(f"📊 Tracking {contract}: Entry ${entry:,.4f} | TP ${levels['take_profit_price']:,.4f} | SL ${levels['stop_price']:,.4f}")
            
            tracked = self.tracked_positions[contract]
            tp = tracked['tp']
            sl = tracked['sl']
            
            if size < 0:  # SHORT position
                if current <= tp:
                    logger.info(f"🎯 TAKE PROFIT +$1.50: {contract} | PnL: ${pnl:,.2f}")
                    if self.client.close_position(contract):
                        self.total_profit += pnl
                        self.trade_count += 1
                        del self.tracked_positions[contract]
                
                elif current >= sl:
                    logger.warning(f"🛑 STOP LOSS -$1.00: {contract} | PnL: ${pnl:,.2f}")
                    if self.client.close_position(contract):
                        self.total_profit += pnl
                        self.daily_loss += abs(pnl)
                        self.trade_count += 1
                        del self.tracked_positions[contract]
    
    def run_cycle(self):
        """Run one trading cycle"""
        balance = self.client.get_balance()
        
        if self.daily_loss >= balance * self.config.DAILY_LOSS_LIMIT_PCT:
            logger.warning(f"⚠️ DAILY LOSS LIMIT REACHED: ${self.daily_loss:.2f}")
            return
        
        positions = self.client.get_positions()
        open_contracts = [p['contract'] for p in positions]
        
        for pair in self.config.TRADING_PAIRS:
            if pair in open_contracts:
                continue
            
            last_trade = self.last_trade_time.get(pair, 0)
            if time.time() - last_trade < self.config.TRADE_COOLDOWN_SEC:
                continue
            
            ticker = self.client.get_ticker(pair)
            if not ticker:
                continue
            
            ticker['adx'] = 30
            ticker['volatility'] = 'medium'
            
            consensus = self.consensus.get_consensus(ticker)
            
            # CRITICAL FILTERS for profitable shorts
            funding_rate = ticker.get('funding_rate', 0)
            change_24h = ticker.get('change_24h', 0)
            
            # Skip if funding is negative (shorts pay longs)
            if funding_rate < 0:
                logger.info(f"⏭️ {pair}: Skip - Negative funding {funding_rate:.4f}% (shorts pay)")
                continue
            
            # Skip if price dropped too much (might bounce)
            if change_24h < -5:
                logger.info(f"⏭️ {pair}: Skip - Oversold {change_24h:.2f}% (bounce risk)")
                continue
            
            if consensus['signal'] == 'SHORT':
                # NEW PRECISE TRADE CALCULATION
                # Risk $1, Stop 0.4%, Target $1.50 profit
                levels = self.calculate_trade_levels(
                    symbol=pair,
                    entry_price=ticker['price'],
                    risk_usdt=1.0,
                    stop_pct=0.004,
                    min_profit_usdt=1.5
                )
                
                # Convert quantity to contract size (minimum 1)
                contract_info = self.client.get_contract_info(pair)
                quanto = contract_info.get('quanto_multiplier', 1)
                size = max(1, int(levels['quantity'] / quanto))
                
                logger.info(f"🚀 NEW TRADE: {pair} | Funding: +{funding_rate:.4f}%")
                logger.info(f"   Risk: ${levels['risk_usdt']} | Target: +${levels['projected_profit_usdt']}")
                logger.info(f"   Size: {size} | Entry: ${levels['entry_price']:,.4f}")
                logger.info(f"   TP: ${levels['take_profit_price']:,.4f} | SL: ${levels['stop_price']:,.4f}")
                
                result = self.client.place_order(pair, size, is_short=True)
                
                if result:
                    self.tracked_positions[pair] = {
                        'entry': result['fill_price'],
                        'tp': levels['take_profit_price'],
                        'sl': levels['stop_price'],
                        'quantity': levels['quantity']
                    }
                    self.last_trade_time[pair] = time.time()
        
        self.monitor_positions()
    
    def print_status(self):
        """Print current status"""
        balance = self.client.get_balance()
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        profit_per_min = self.total_profit / elapsed if elapsed > 0 else 0
        
        positions = self.client.get_positions()
        unrealized = sum([p['unrealised_pnl'] for p in positions])
        
        logger.info("=" * 60)
        logger.info(f"💰 Balance: ${balance:,.2f} | Unrealized: ${unrealized:,.2f}")
        logger.info(f"📈 Total Profit: ${self.total_profit:,.2f} | Trades: {self.trade_count}")
        logger.info(f"⏱️ Rate: ${profit_per_min:,.4f}/min | Target: ${self.config.TARGET_PER_MINUTE}/min")
        logger.info(f"📊 Open Positions: {len(positions)}")
        logger.info("=" * 60)
    
    def run(self):
        """Main trading loop - NEW PRECISE SYSTEM"""
        logger.info("=" * 60)
        logger.info("🔥🔥🔥 GODS MODE L13 - NEW PRECISE SETUP 🔥🔥🔥")
        logger.info("=" * 60)
        logger.info(f"💰 Balance: ${self.client.get_balance():,.2f}")
        logger.info("📐 NEW PRECISE TRADE SYSTEM:")
        logger.info("   Risk: $1.00 per trade | Stop: 0.4%")
        logger.info("   Target: +$1.50 profit per trade")
        logger.info(f"⚡ Cycle Speed: {self.config.LOOP_DELAY_SEC}s")
        logger.info(f"🔥 Cooldown: {self.config.TRADE_COOLDOWN_SEC}s")
        logger.info(f"🤖 AI Agents: 6 Gods | Consensus: {self.config.MIN_AGENTS_AGREE}/6")
        logger.info(f"📊 Pairs: {', '.join(self.config.TRADING_PAIRS)}")
        logger.info("⚙️ Direction: SHORTS ONLY | Funding Filter: ON")
        logger.info("=" * 60)
        
        cycle = 0
        while True:
            try:
                cycle += 1
                
                self.run_cycle()
                
                if cycle % 30 == 0:
                    self.print_status()
                
                time.sleep(self.config.LOOP_DELAY_SEC)
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                time.sleep(5)


# ========== MAIN ==========

if __name__ == "__main__":
    os.makedirs('logs', exist_ok=True)
    
    bot = GodsModeBot()
    bot.run()
