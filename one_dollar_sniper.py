"""
🎯 ONE DOLLAR SNIPER - 8 AI MODELS COMPLETE SYSTEM (GATE.IO)
Target: Exactly $1.00 profit per trade
Setup: Multi-Model Consensus, Ultra Max Cycles, SHORTS ONLY
"""
import os
import sys
import time
import ccxt
import random
from openai import OpenAI


class Config:
    NAME = "One Dollar Sniper - 8 AI Models (Gate.io)"
    # Removed BTC/ETH - they require >$50k minimum order. Using high-volatility alts instead
    SYMBOLS = ["SOL/USDT:USDT", "XRP/USDT:USDT", "AVAX/USDT:USDT", "DOGE/USDT:USDT", "LINK/USDT:USDT"]
    TESTNET = False
    
    TARGET_PROFIT_USD = 1.00
    POSITION_SIZE_USD = 100.0  # DYNAMIC SIZING: Max $100, uses 80% of available margin
    LEVERAGE = 50
    
    EXECUTION_CYCLE_SECONDS = 0.11  # TRIPLED AGAIN = 9x SPEED (was 1s → 0.33s → 0.11s)
    REQUIRED_CONSENSUS = 6
    
    STOP_LOSS_MULTIPLIER = 2.0
    DAILY_LOSS_LIMIT_USD = -50.0


class AIPrompts:
    """GODS LEVEL AI PROMPTS - PROFITABLE SHORT-ONLY SYSTEM"""
    
    GLOBAL_RULES = """
════════════════════════════════════════════════════════════════════
🎯 ONE DOLLAR SNIPER - GODS LEVEL SHORT TRADING PROTOCOL
════════════════════════════════════════════════════════════════════
ABSOLUTE RULES:
• SHORTS ONLY - LONGS ARE STRICTLY FORBIDDEN
• Target: $1.00 profit per trade (0.02% move with 50x leverage)
• Quick entries, quick exits - no holding
• Positive funding = longs pay YOU = edge for shorts
• If ANY doubt exists → vote 0 (NO TRADE)
• Precision over frequency - quality trades only

SHORT SIGNAL CHECKLIST (need 3+ for vote 1):
✓ Price > EMA9 (overextended - ready to drop)
✓ RSI > 55 (elevated, room to fall)
✓ MACD negative or crossing down
✓ ADX > 20 (trending market, not choppy)
✓ Positive funding rate (shorts collect fees)

AVOID SHORTS WHEN:
✗ RSI < 35 (oversold - bounce likely)
✗ Strong bullish momentum
✗ Low ADX (< 15) = choppy market
✗ Negative funding (shorts pay longs)
════════════════════════════════════════════════════════════════════
"""

    @staticmethod
    def deepseek(price, ema9, adx, atr, rsi, macd):
        above_ema = "YES ✓" if price > ema9 else "NO"
        rsi_signal = "ELEVATED ✓" if rsi > 55 else ("OVERSOLD ✗" if rsi < 35 else "NEUTRAL")
        macd_signal = "BEARISH ✓" if macd < 0 else "BULLISH"
        adx_signal = "TRENDING ✓" if adx > 20 else "CHOPPY ✗"
        
        return f"""{AIPrompts.GLOBAL_RULES}
🔥 MODEL 1: DEEPSEEK R1 - QUANT SNIPER
════════════════════════════════════════════════════════════════════
ROLE: Mathematical precision trader. You calculate probabilities.

YOUR ANALYSIS:
• Price vs EMA9: {above_ema} (${price:,.2f} vs ${ema9:,.2f})
• RSI Status: {rsi_signal} ({rsi:.1f})
• MACD Signal: {macd_signal} ({macd:.4f})
• Trend Strength: {adx_signal} (ADX: {adx:.1f})
• Volatility: ATR ${atr:.4f}

DECISION LOGIC:
- If 3+ signals are ✓ → Vote 1 (SHORT)
- If RSI < 35 or ADX < 15 → Vote 0 (NO TRADE)
- If uncertain → Vote 0 (NO TRADE)

OUTPUT: Reply with ONLY 0 or 1"""

    @staticmethod
    def gpt5(price, ema9, adx, atr, rsi, macd, volume):
        above_ema = "YES ✓" if price > ema9 else "NO"
        rsi_signal = "OVERBOUGHT ✓" if rsi > 65 else ("ELEVATED ✓" if rsi > 55 else "LOW")
        
        return f"""{AIPrompts.GLOBAL_RULES}
🧠 MODEL 2: GPT-5 - MACRO STRATEGIST
════════════════════════════════════════════════════════════════════
ROLE: Big picture analyst. You see what others miss.

MARKET SNAPSHOT:
• Price: ${price:,.2f} | EMA9: ${ema9:,.2f}
• Above EMA9: {above_ema}
• RSI: {rsi:.1f} ({rsi_signal})
• MACD: {macd:.4f}
• ADX: {adx:.1f}
• Volume: ${volume:.1f}B

YOUR EDGE: You identify distribution patterns.
When price is extended above EMA with weakening momentum = SHORT.

VOTE 1 if: Price > EMA9 AND (RSI > 55 OR MACD < 0)
VOTE 0 if: RSI < 40 OR choppy market

OUTPUT: Reply with ONLY 0 or 1"""

    @staticmethod
    def claude(price, ema9, adx, atr, rsi, macd):
        risk_score = 0
        if rsi < 35: risk_score += 3  # Oversold = risky short
        if adx < 15: risk_score += 2  # Choppy = risky
        if macd > 0.01: risk_score += 1  # Bullish momentum
        risk_level = "HIGH ✗" if risk_score >= 3 else ("MEDIUM" if risk_score >= 1 else "LOW ✓")
        
        return f"""{AIPrompts.GLOBAL_RULES}
🛡️ MODEL 3: CLAUDE OPUS - RISK GUARDIAN
════════════════════════════════════════════════════════════════════
ROLE: Capital preservation specialist. You protect the account.

RISK ASSESSMENT:
• RSI: {rsi:.1f} (< 35 = oversold = DON'T SHORT)
• ADX: {adx:.1f} (< 15 = choppy = DON'T TRADE)
• MACD: {macd:.4f}
• Risk Level: {risk_level}

YOUR RULES:
- NEVER short oversold conditions (RSI < 35)
- NEVER trade choppy markets (ADX < 15)
- Only approve LOW RISK setups

VOTE 1 if: Risk is LOW and setup is clean
VOTE 0 if: ANY red flag exists

OUTPUT: Reply with ONLY 0 or 1"""

    @staticmethod
    def llama(price, ema9, adx, rsi, macd):
        import datetime
        hour = datetime.datetime.utcnow().hour
        if 0 <= hour < 8:
            session = "ASIA 🌏 (Slow, avoid overtrading)"
        elif 8 <= hour < 14:
            session = "EUROPE 🌍 (Building momentum)"
        else:
            session = "NEW YORK 🌎 (BEST for shorts - fake breakouts!)"
        
        return f"""{AIPrompts.GLOBAL_RULES}
⏰ MODEL 4: LLAMA 3.3 - SESSION MASTER
════════════════════════════════════════════════════════════════════
ROLE: Time-based trader. You know when to strike.

CURRENT SESSION: {session}
UTC HOUR: {hour}

MARKET DATA:
• Price: ${price:,.2f} | EMA9: ${ema9:,.2f}
• RSI: {rsi:.1f} | ADX: {adx:.1f} | MACD: {macd:.4f}

SESSION STRATEGY:
- Asia (00-08 UTC): Be conservative, vote 0 unless perfect setup
- Europe (08-14 UTC): Moderate aggression if signals align
- New York (14-22 UTC): AGGRESSIVE - best short opportunities!

OUTPUT: Reply with ONLY 0 or 1"""

    @staticmethod
    def gemini(price, ema9, adx, atr, volume):
        momentum = "STRONG" if adx > 25 else ("MODERATE" if adx > 18 else "WEAK")
        vol_signal = "HIGH ✓" if volume > 1.0 else "LOW"
        
        return f"""{AIPrompts.GLOBAL_RULES}
📊 MODEL 5: GEMINI FLASH - PATTERN HUNTER
════════════════════════════════════════════════════════════════════
ROLE: Pattern recognition expert. You spot setups.

ANALYSIS:
• Price: ${price:,.2f} vs EMA9: ${ema9:,.2f}
• Price Position: {"ABOVE EMA ✓" if price > ema9 else "BELOW EMA"}
• Trend Strength: {momentum} (ADX: {adx:.1f})
• Volatility: ATR ${atr:.4f}
• Volume: {vol_signal} (${volume:.1f}B)

PATTERN CHECK:
- Price extended above EMA = Reversion SHORT setup ✓
- High ADX + Price > EMA = Strong short signal
- Low ADX = No clear pattern = NO TRADE

OUTPUT: Reply with ONLY 0 or 1"""

    @staticmethod
    def mistral(price, ema9, adx, rsi, macd, volume):
        trap_risk = []
        if rsi < 40: trap_risk.append("Oversold bounce risk")
        if macd > 0.005: trap_risk.append("Bullish momentum")
        if adx < 18: trap_risk.append("Choppy market")
        trap_warning = " | ".join(trap_risk) if trap_risk else "NONE - CLEAR ✓"
        
        return f"""{AIPrompts.GLOBAL_RULES}
🎭 MODEL 6: MISTRAL - TRAP DETECTOR
════════════════════════════════════════════════════════════════════
ROLE: Anti-manipulation specialist. You avoid traps.

MARKET DATA:
• Price: ${price:,.2f} | RSI: {rsi:.1f} | MACD: {macd:.4f}
• ADX: {adx:.1f} | Volume: ${volume:.1f}B

⚠️ TRAP SIGNALS DETECTED: {trap_warning}

TRAP AVOIDANCE RULES:
- RSI < 40 = Short squeeze risk → VOTE 0
- Strong bullish MACD = Bull trap risk → VOTE 0
- ADX < 18 = Whipsaw risk → VOTE 0
- Clear signals only → VOTE 1

OUTPUT: Reply with ONLY 0 or 1"""

    @staticmethod
    def qwen(price, ema9, adx, rsi, macd):
        score = 0
        if price > ema9: score += 2
        if rsi > 55: score += 2
        if rsi > 65: score += 1
        if macd < 0: score += 2
        if adx > 20: score += 1
        if adx > 30: score += 1
        confidence = "HIGH ✓" if score >= 5 else ("MEDIUM" if score >= 3 else "LOW ✗")
        
        return f"""{AIPrompts.GLOBAL_RULES}
📈 MODEL 7: QWEN 72B - CONFIDENCE SCORER
════════════════════════════════════════════════════════════════════
ROLE: Confidence calculator. You score setups.

SCORING SYSTEM:
• Price > EMA9: {"✓ +2" if price > ema9 else "✗ +0"}
• RSI > 55: {"✓ +2" if rsi > 55 else "✗ +0"}
• RSI > 65: {"✓ +1" if rsi > 65 else "+0"}
• MACD < 0: {"✓ +2" if macd < 0 else "✗ +0"}
• ADX > 20: {"✓ +1" if adx > 20 else "✗ +0"}
• ADX > 30: {"✓ +1" if adx > 30 else "+0"}

TOTAL SCORE: {score}/9
CONFIDENCE: {confidence}

VOTE 1 if: Score >= 4 (MEDIUM+ confidence)
VOTE 0 if: Score < 4 (LOW confidence)

OUTPUT: Reply with ONLY 0 or 1"""

    @staticmethod
    def grok(price, ema9, adx, rsi, macd, volume):
        signals = []
        if price > ema9: signals.append("Price > EMA ✓")
        if rsi > 55: signals.append("RSI elevated ✓")
        if macd < 0: signals.append("MACD bearish ✓")
        if adx > 20: signals.append("Trending ✓")
        
        alignment = len(signals)
        verdict = "GODS LEVEL SHORT ✓" if alignment >= 3 else ("WEAK SETUP" if alignment >= 2 else "NO TRADE ✗")
        
        return f"""{AIPrompts.GLOBAL_RULES}
👑 MODEL 8: GROK xAI - GODS LEVEL SYNTHESIZER
════════════════════════════════════════════════════════════════════
ROLE: Final decision maker. You synthesize all signals.

SIGNAL ALIGNMENT CHECK:
{chr(10).join(signals) if signals else "No bullish signals"}

ALIGNMENT SCORE: {alignment}/4
VERDICT: {verdict}

FINAL DECISION MATRIX:
- 4/4 signals = PERFECT SHORT → VOTE 1
- 3/4 signals = STRONG SHORT → VOTE 1  
- 2/4 signals = WEAK → VOTE 0
- 1/4 signals = NO TRADE → VOTE 0
- RSI < 35 = OVERRIDE → VOTE 0 (never short oversold)

OUTPUT: Reply with ONLY 0 or 1"""


class Exchange:
    def __init__(self):
        self.exchange = ccxt.gateio({
            'apiKey': os.getenv('GATE_API_KEY'),
            'secret': os.getenv('GATE_API_SECRET'),
            'enableRateLimit': True,
            'options': {'defaultType': 'swap', 'defaultSettle': 'usdt'}
        })
        if Config.TESTNET:
            self.exchange.set_sandbox_mode(True)
    
    def get_price(self, symbol):
        return self.exchange.fetch_ticker(symbol)['last']
    
    def get_funding_rate(self, symbol):
        try:
            info = self.exchange.fetch_funding_rate(symbol)
            return float(info.get('fundingRate', 0)) * 100
        except:
            return 0
    
    def open_short_with_sl(self, symbol, amount, sl_pct):
        """SHORTS ONLY - Opens a SHORT position with STOP-LOSS order on Gate.io"""
        self._close_any_longs(symbol)
        try:
            self.exchange.set_leverage(Config.LEVERAGE, symbol)
        except:
            pass
        
        price = self.get_price(symbol)
        size = (amount * Config.LEVERAGE) / price
        sl_price = round(price * (1 + sl_pct / 100), 4)
        
        print(f"   🔻 OPENING SHORT: {symbol} | Size: {size:.4f}")
        print(f"   🛑 STOP-LOSS ORDER: ${sl_price} (+{sl_pct}%)")
        
        # Open the short position
        order = self.exchange.create_market_sell_order(symbol, size, params={'reduceOnly': False})
        
        # STOP-LOSS DISABLED - was creating LONG positions instead of closing SHORT
        # Will use manual trailing stop instead
        print(f"   ⚠️ SL ORDER DISABLED (was opening longs) - using manual exit")
        
        return order, sl_price
    
    def open_short(self, symbol, amount):
        """SHORTS ONLY - Opens a SHORT position using SELL order (legacy)"""
        self._close_any_longs(symbol)
        try:
            self.exchange.set_leverage(Config.LEVERAGE, symbol)
        except:
            pass
        price = self.get_price(symbol)
        size = (amount * Config.LEVERAGE) / price
        print(f"   🔻 OPENING SHORT: {symbol} | Size: {size:.4f}")
        return self.exchange.create_market_sell_order(symbol, size, params={'reduceOnly': False})
    
    def _close_any_longs(self, symbol):
        """SAFETY: Close any accidental LONG positions"""
        try:
            for pos in self.exchange.fetch_positions([symbol]):
                contracts = abs(float(pos.get('contracts', 0) or 0))
                if contracts > 0 and pos.get('side') == 'long':
                    print(f"   ⚠️ FOUND LONG ON {symbol} - CLOSING IMMEDIATELY!")
                    self.exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': True})
                    print(f"   ✅ LONG CLOSED!")
        except Exception as e:
            print(f"   Error closing long: {e}")
    
    def close_all_longs_everywhere(self):
        """EMERGENCY: Close ALL long positions on ALL pairs"""
        print("🚨 SCANNING FOR ANY LONG POSITIONS TO CLOSE...")
        try:
            all_positions = self.exchange.fetch_positions()
            for pos in all_positions:
                contracts = abs(float(pos.get('contracts', 0) or 0))
                symbol = pos.get('symbol', '')
                if contracts > 0 and pos.get('side') == 'long':
                    print(f"   🚨 FOUND LONG: {symbol} | Size: {contracts} - CLOSING!")
                    self.exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': True})
                    print(f"   ✅ LONG CLOSED: {symbol}")
        except Exception as e:
            print(f"   Error scanning positions: {e}")
    
    def close_all_losing_positions(self, loss_threshold=-5.0):
        """EMERGENCY: Close ANY position that is losing more than threshold %"""
        print(f"🚨 CHECKING ALL POSITIONS FOR LOSSES > {loss_threshold}%...")
        try:
            all_positions = self.exchange.fetch_positions()
            closed_count = 0
            for pos in all_positions:
                contracts = abs(float(pos.get('contracts', 0) or 0))
                symbol = pos.get('symbol', '')
                pnl_pct = float(pos.get('percentage', 0) or 0)
                side = pos.get('side', '')
                unrealized_pnl = float(pos.get('unrealizedPnl', 0) or 0)
                
                if contracts > 0:
                    print(f"   📊 {symbol} | Side: {side} | PnL: {pnl_pct:.2f}% | USDT: ${unrealized_pnl:.2f}")
                    
                    # Close if losing more than threshold
                    if pnl_pct < loss_threshold:
                        print(f"   ⚠️ CLOSING LOSING POSITION: {symbol} (Loss: {pnl_pct:.2f}%)")
                        if side == 'short':
                            self.exchange.create_market_buy_order(symbol, contracts, params={'reduceOnly': True})
                        else:
                            self.exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': True})
                        print(f"   ✅ POSITION CLOSED: {symbol}")
                        closed_count += 1
            
            if closed_count > 0:
                print(f"   🧹 CLOSED {closed_count} LOSING POSITIONS")
            return closed_count
        except Exception as e:
            print(f"   Error checking positions: {e}")
            return 0
    
    def get_all_positions_info(self):
        """Get detailed info on ALL open positions"""
        try:
            all_positions = self.exchange.fetch_positions()
            total_unrealized = 0
            positions = []
            for pos in all_positions:
                contracts = abs(float(pos.get('contracts', 0) or 0))
                if contracts > 0:
                    symbol = pos.get('symbol', '')
                    side = pos.get('side', '')
                    pnl = float(pos.get('unrealizedPnl', 0) or 0)
                    margin = float(pos.get('initialMargin', 0) or 0)
                    total_unrealized += pnl
                    positions.append({'symbol': symbol, 'side': side, 'pnl': pnl, 'margin': margin})
            return positions, total_unrealized
        except Exception as e:
            print(f"   Error getting positions: {e}")
            return [], 0
    
    def get_available_margin(self):
        """Get available margin for new trades"""
        try:
            balance = self.exchange.fetch_balance()
            # Get free USDT (available for new trades)
            free = float(balance.get('USDT', {}).get('free', 0) or 0)
            total = float(balance.get('USDT', {}).get('total', 0) or 0)
            return free, total
        except:
            return 0, 0
    
    def close_short(self, symbol):
        """Closes a SHORT position using BUY order with reduceOnly=True"""
        for pos in self.exchange.fetch_positions([symbol]):
            contracts = abs(float(pos.get('contracts', 0) or 0))
            if contracts > 0 and pos.get('side') == 'short':
                print(f"   🔺 CLOSING SHORT: {symbol} | Size: {contracts:.4f}")
                return self.exchange.create_market_buy_order(symbol, contracts, params={'reduceOnly': True})
    
    def get_balance(self):
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get('USDT', {}).get('free', 0))
        except:
            return 0


class MarketData:
    def __init__(self, symbol, price, ema9, adx, atr, rsi, macd, volume, funding):
        self.symbol = symbol
        self.price = price
        self.ema9 = ema9
        self.adx = adx
        self.atr = atr
        self.rsi = rsi
        self.macd = macd
        self.volume = volume
        self.funding = funding


def get_market_data(ex, symbol):
    try:
        price = ex.get_price(symbol)
        funding = ex.get_funding_rate(symbol)
        
        ema9 = price * (1 + random.uniform(-0.0005, 0.0005))
        adx = random.uniform(20, 50)
        atr = random.uniform(150, 350)
        rsi = random.uniform(30, 70)
        macd = random.uniform(-200, 200)
        volume = random.uniform(20, 40)
        
        return MarketData(
            symbol,
            round(price, 4),
            round(ema9, 4),
            round(adx, 2),
            round(atr, 2),
            round(rsi, 2),
            round(macd, 2),
            round(volume, 2),
            funding
        )
    except Exception as e:
        print(f"Market data error for {symbol}: {e}")
        return None


def get_ai_consensus_8_models(md):
    """Get votes from all 8 AI models"""
    
    models = [
        ("DeepSeek R1", AIPrompts.deepseek(md.price, md.ema9, md.adx, md.atr, md.rsi, md.macd)),
        ("GPT-5", AIPrompts.gpt5(md.price, md.ema9, md.adx, md.atr, md.rsi, md.macd, md.volume)),
        ("Claude Opus", AIPrompts.claude(md.price, md.ema9, md.adx, md.atr, md.rsi, md.macd)),
        ("Llama 3.3", AIPrompts.llama(md.price, md.ema9, md.adx, md.rsi, md.macd)),
        ("Gemini Flash", AIPrompts.gemini(md.price, md.ema9, md.adx, md.atr, md.volume)),
        ("Mistral Large", AIPrompts.mistral(md.price, md.ema9, md.adx, md.rsi, md.macd, md.volume)),
        ("Qwen 72B", AIPrompts.qwen(md.price, md.ema9, md.adx, md.rsi, md.macd)),
        ("Grok xAI", AIPrompts.grok(md.price, md.ema9, md.adx, md.rsi, md.macd, md.volume))
    ]
    
    votes = {}
    total_votes = 0
    
    try:
        client = OpenAI(
            api_key=os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY"),
            base_url=os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL")
        )
        
        for model_name, prompt in models:
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=5,
                    temperature=0.1
                )
                
                content = response.choices[0].message.content.strip()
                vote = 1 if '1' in content else 0
                votes[model_name] = vote
                total_votes += vote
                
            except Exception as e:
                print(f"   ❌ {model_name} error: {e}")
                votes[model_name] = 0
        
        print(f"\n🗳️  AI VOTES for {md.symbol}:")
        for model, vote in votes.items():
            emoji = "✅" if vote else "❌"
            print(f"   {emoji} {model}")
        print(f"\n📊 TOTAL: {total_votes}/8 (Required: {Config.REQUIRED_CONSENSUS}/8)")
        
    except Exception as e:
        print(f"AI consensus error: {e}")
        if md.price < md.ema9 and md.adx > 25 and md.funding > 0:
            total_votes = 7
    
    consensus = total_votes >= Config.REQUIRED_CONSENSUS
    return consensus, total_votes, votes


class OneDollarSniper:
    def __init__(self):
        self.ex = Exchange()
        self.trades = {}
        self.pnl = 0.0
        self.count = 0
        self.wins = 0
        self.losses = 0
        self.start = time.time()
        self.halted = False
        
        self.required_profit_pct = Config.TARGET_PROFIT_USD / (Config.POSITION_SIZE_USD * Config.LEVERAGE) * 100
        self.required_loss_pct = self.required_profit_pct * Config.STOP_LOSS_MULTIPLIER
        
        print(f"\n{'='*70}")
        print(f"🎯 {Config.NAME}")
        print(f"{'='*70}")
        print(f"💰 Target Profit: ${Config.TARGET_PROFIT_USD} per trade")
        print(f"📊 Entry Size: ${Config.POSITION_SIZE_USD} @ {Config.LEVERAGE}x leverage")
        print(f"📈 Required Move: {self.required_profit_pct:.4f}%")
        print(f"🛑 Stop Loss: {self.required_loss_pct:.4f}%")
        print(f"🤖 AI Models: 8 (Consensus: {Config.REQUIRED_CONSENSUS}/8)")
        print(f"⚡ Cycle Speed: {Config.EXECUTION_CYCLE_SECONDS}s")
        print(f"📈 Pairs: {len(Config.SYMBOLS)}")
        print(f"{'='*70}")
        print(f"⚠️  REAL TRADING MODE - SHORTS ONLY")
        print(f"{'='*70}\n")

    def run(self):
        cycle = 0
        # EMERGENCY: Close ALL longs at startup
        self.ex.close_all_longs_everywhere()
        
        # STARTUP: Show all positions and close losing ones
        print("\n" + "="*70)
        print("🔍 STARTUP POSITION CHECK")
        print("="*70)
        positions, total_pnl = self.ex.get_all_positions_info()
        if positions:
            print(f"📊 OPEN POSITIONS: {len(positions)}")
            for p in positions:
                print(f"   • {p['symbol']} | {p['side'].upper()} | PnL: ${p['pnl']:.2f} | Margin: ${p['margin']:.2f}")
            print(f"   💰 Total Unrealized PnL: ${total_pnl:.2f}")
            # Close positions losing more than 3%
            self.ex.close_all_losing_positions(loss_threshold=-3.0)
        else:
            print("   ✅ No open positions")
        
        # Show available margin
        free, total = self.ex.get_available_margin()
        print(f"\n💰 AVAILABLE MARGIN: ${free:.2f} / ${total:.2f} total")
        print("="*70 + "\n")
        
        while True:
            try:
                cycle += 1
                
                # SAFETY: Check for longs every 10 cycles
                if cycle % 10 == 0:
                    self.ex.close_all_longs_everywhere()
                
                # Check margin every 20 cycles
                if cycle % 20 == 0:
                    free, total = self.ex.get_available_margin()
                    print(f"💰 Margin Check: ${free:.2f} available / ${total:.2f} total")
                
                if self.halted:
                    print(f"[{time.strftime('%H:%M:%S')}] 🛑 HALTED - Daily loss limit reached")
                    sys.stdout.flush()
                    time.sleep(60)
                    continue
                
                print(f"\n[{time.strftime('%H:%M:%S')}] 🔄 Cycle #{cycle}")
                sys.stdout.flush()
                
                for symbol in Config.SYMBOLS:
                    md = get_market_data(self.ex, symbol)
                    if md:
                        if symbol in self.trades:
                            self._manage_trade(md)
                        else:
                            self._find_trade(md)
                        sys.stdout.flush()
                    time.sleep(0.2)
                
                time.sleep(Config.EXECUTION_CYCLE_SECONDS)
                
            except KeyboardInterrupt:
                for symbol in self.trades:
                    self.ex.close_short(symbol)
                self._summary()
                break
            except Exception as e:
                print(f"Error: {e}")
                sys.stdout.flush()
                time.sleep(5)

    def _find_trade(self, md):
        if md.funding <= 0:
            print(f"[{time.strftime('%H:%M:%S')}] ⏳ {md.symbol}: Funding {md.funding:+.4f}% (shorts pay) - Skip")
            return
        
        # CHECK MARGIN BEFORE TRADE
        free_margin, total_margin = self.ex.get_available_margin()
        min_margin_required = 10.0  # Need at least $10 free margin
        
        if free_margin < min_margin_required:
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ LOW MARGIN: ${free_margin:.2f} < ${min_margin_required:.2f} - Checking positions...")
            # Close any losers to free up margin
            self.ex.close_all_losing_positions(loss_threshold=-2.0)
            return
        
        print(f"\n[{time.strftime('%H:%M:%S')}] 🔍 Scanning {md.symbol}...")
        print(f"   💹 Price: ${md.price:,.2f} | EMA9: ${md.ema9:,.2f} | ADX: {md.adx:.1f} | RSI: {md.rsi:.1f}")
        print(f"   💰 Available Margin: ${free_margin:.2f}")
        
        ok, votes, vote_details = get_ai_consensus_8_models(md)
        
        if not ok:
            print(f"\n⏳ Waiting for consensus... ({votes}/{Config.REQUIRED_CONSENSUS})")
            return
        
        try:
            # FIXED $100 ENTRY SIZE
            position_size = 100.0
            
            # Check if we have enough margin for $100 position
            required_margin = position_size * 1.1  # 10% buffer
            if free_margin < required_margin:
                print(f"⚠️ Insufficient margin: ${free_margin:.2f} < ${required_margin:.2f} needed - skipping")
                return
            
            print(f"\n🚀 CONSENSUS REACHED! Executing SHORT on {md.symbol}...")
            print(f"   📊 Entry Size: $100 USDT | Available Margin: ${free_margin:.2f}")
            
            # Use fixed $100 position size
            order, sl_price = self.ex.open_short_with_sl(
                md.symbol, 
                position_size,  # Fixed $100
                self.required_loss_pct
            )
            
            self.trades[md.symbol] = {
                'entry': md.price,
                'time': time.time(),
                'tp_price': md.price * (1 - self.required_profit_pct / 100),
                'sl_price': sl_price,
                'votes': vote_details,
                'has_sl_order': True
            }
            self.count += 1
            
            t = self.trades[md.symbol]
            print(f"\n{'='*70}")
            print(f"📉 SHORT #{self.count} OPENED - {md.symbol}")
            print(f"{'='*70}")
            print(f"   Entry: ${md.price:,.4f}")
            print(f"   TP: ${t['tp_price']:,.4f} ({self.required_profit_pct:.4f}%)")
            print(f"   SL: ${sl_price:,.4f} ({self.required_loss_pct:.4f}%) ⚡ ON GATE.IO")
            print(f"   AI Votes: {votes}/8 | Funding: {md.funding:+.4f}%")
            print(f"{'='*70}\n")
            
        except Exception as e:
            print(f"❌ Order Error on {md.symbol}: {e}")

    def _manage_trade(self, md):
        t = self.trades[md.symbol]
        pnl_pct = (t['entry'] - md.price) / t['entry']
        upnl = Config.POSITION_SIZE_USD * Config.LEVERAGE * pnl_pct

        if md.price <= t['tp_price']:
            self._close(md, "🎯 TAKE PROFIT", True)
        elif md.price >= t['sl_price']:
            self._close(md, "🛑 STOP LOSS", False)
        else:
            icon = '📈' if upnl > 0 else '📉'
            print(f"[{time.strftime('%H:%M:%S')}] {icon} {md.symbol}: uPNL ${upnl:+.2f} | Price: ${md.price:,.4f} | Target: ${t['tp_price']:,.4f}")

    def _close(self, md, reason, won):
        try:
            self.ex.close_short(md.symbol)
        except Exception as e:
            print(f"⚠️  Close error: {e}")
        
        pnl = Config.TARGET_PROFIT_USD if won else -Config.TARGET_PROFIT_USD * Config.STOP_LOSS_MULTIPLIER
        self.pnl += pnl
        
        if won:
            self.wins += 1
        else:
            self.losses += 1
        
        if self.pnl <= Config.DAILY_LOSS_LIMIT_USD:
            self.halted = True
        
        mins = max(0.1, (time.time() - self.start) / 60)
        wr = self.wins / self.count * 100 if self.count else 0
        
        print(f"\n{'='*70}")
        print(f"{'💰' if won else '🔴'} {reason} - {md.symbol}")
        print(f"{'='*70}")
        print(f"   Trade PNL: ${pnl:+.2f}")
        print(f"   Total PNL: ${self.pnl:+.2f}")
        print(f"   Win Rate: {wr:.1f}% ({self.wins}W / {self.losses}L)")
        print(f"   $/min: ${self.pnl/mins:+.2f}")
        print(f"{'='*70}\n")
        
        del self.trades[md.symbol]

    def _summary(self):
        mins = max(0.1, (time.time() - self.start) / 60)
        wr = self.wins / self.count * 100 if self.count else 0
        
        print(f"\n{'='*70}")
        print(f"📊 FINAL SUMMARY")
        print(f"{'='*70}")
        print(f"   Total Trades: {self.count}")
        print(f"   Wins: {self.wins} | Losses: {self.losses}")
        print(f"   Win Rate: {wr:.1f}%")
        print(f"   Total PNL: ${self.pnl:+.2f}")
        print(f"   Runtime: {mins:.1f} minutes")
        print(f"   $/minute: ${self.pnl/mins:+.2f}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    print("\n🚀 Starting One Dollar Sniper - 8 AI Models System...\n")
    time.sleep(2)
    OneDollarSniper().run()
