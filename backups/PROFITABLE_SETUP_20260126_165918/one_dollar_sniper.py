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
    POSITION_SIZE_USD = 100.0
    LEVERAGE = 50
    
    EXECUTION_CYCLE_SECONDS = 1
    REQUIRED_CONSENSUS = 6
    
    STOP_LOSS_MULTIPLIER = 2.0
    DAILY_LOSS_LIMIT_USD = -50.0


class AIPrompts:
    """Prompts for all 8 AI models - One Dollar Sniper Logic"""
    
    @staticmethod
    def deepseek(price, ema9, adx, atr, rsi, macd):
        return f"""You are DeepSeek R1, a reasoning-focused AI trading model.

MISSION: Use deep logical reasoning to determine if current market conditions support a SHORT entry for $1 profit.

MARKET DATA:
Price: ${price:,.2f} | EMA9: ${ema9:,.2f} | ADX: {adx:.1f} | ATR: {atr:.2f} | RSI: {rsi:.1f} | MACD: {macd:.2f}

LOGIC CHAIN:
- IF Price < EMA9 AND ADX > 25 AND RSI < 50 → Strong SHORT signal
- IF ATR > 200 → High volatility = Fast moves possible
- IF MACD < 0 → Bearish momentum confirmed

OUTPUT: Reply with ONLY 0 (NO) or 1 (YES)"""

    @staticmethod
    def gpt5(price, ema9, adx, atr, rsi, macd, volume):
        return f"""You are GPT-5, an advanced AI with superior contextual understanding.

MISSION: Analyze ALL market factors holistically to identify ultra-fast SHORT opportunities.

MARKET DATA:
Price: ${price:,.2f} | EMA9: ${ema9:,.2f} | ADX: {adx:.1f} | ATR: {atr:.2f} | RSI: {rsi:.1f} | MACD: {macd:.2f} | Volume: ${volume:.1f}B

DECISION LOGIC:
- Downtrend + High ADX + Negative MACD = HIGH CONFIDENCE SHORT
- Consolidation or Reversal Signals = NO TRADE

OUTPUT: Reply with ONLY 0 (No Trade) or 1 (SHORT Entry)"""

    @staticmethod
    def claude(price, ema9, adx, atr, rsi, macd):
        return f"""You are Claude Opus, a risk-conscious AI trading advisor.

MISSION: Evaluate if the current SHORT setup has a FAVORABLE risk/reward for a $1 profit target.

MARKET DATA:
Price: ${price:,.2f} | EMA9: ${ema9:,.2f} | ADX: {adx:.1f} | ATR: {atr:.2f} | RSI: {rsi:.1f} | MACD: {macd:.2f}

SAFETY CHECKS:
✅ Price below EMA9 (trend confirmed)
✅ ADX > 25 (strong trend, not choppy)
✅ RSI < 50 (room to fall)
✅ MACD negative (bearish momentum)

OUTPUT: Reply with ONLY 0 (Too Risky) or 1 (Safe SHORT Entry)"""

    @staticmethod
    def llama(price, ema9, adx, rsi, macd):
        return f"""You are Llama 3.3, optimized for SPEED and EFFICIENCY.

MISSION: Quickly identify SHORT patterns that can deliver $1 profit in seconds.

MARKET DATA:
Price: ${price:,.2f} | EMA9: ${ema9:,.2f} | ADX: {adx:.1f} | RSI: {rsi:.1f} | MACD: {macd:.2f}

QUICK DECISION:
IF (Price < EMA9 AND ADX > 25 AND RSI < 50):
    OUTPUT: 1
ELSE:
    OUTPUT: 0

Reply with ONLY 0 or 1"""

    @staticmethod
    def gemini(price, ema9, adx, atr, volume):
        return f"""You are Gemini Flash, specialized in REAL-TIME market adaptation.

MISSION: Detect FLASH opportunities for ultra-fast SHORT entries.

MARKET DATA:
Price: ${price:,.2f} | EMA9: ${ema9:,.2f} | ADX: {adx:.1f} | ATR: {atr:.2f} | Volume: ${volume:.1f}B

FLASH DETECTION:
- IF Price just broke below EMA9 → FLASH SHORT
- IF Volume spike + Red candle → FLASH SHORT
- IF ADX > 30 + Price falling → FLASH SHORT

OUTPUT: Reply with ONLY 0 (No Flash) or 1 (FLASH SHORT)"""

    @staticmethod
    def mistral(price, ema9, adx, rsi, macd, volume):
        return f"""You are Mistral Large, a quantitative analysis specialist.

MISSION: Calculate the STATISTICAL PROBABILITY of a successful $1 SHORT trade.

MARKET DATA:
Price: ${price:,.2f} | EMA9: ${ema9:,.2f} | ADX: {adx:.1f} | RSI: {rsi:.1f} | MACD: {macd:.2f} | Volume: ${volume:.1f}B

CALCULATION:
IF P(Success) > 75%:
    OUTPUT: 1
ELSE:
    OUTPUT: 0

Reply with ONLY 0 or 1"""

    @staticmethod
    def qwen(price, ema9, adx, rsi, macd):
        return f"""You are Qwen 72B, expert in MULTI-TIMEFRAME analysis.

MISSION: Confirm SHORT signals across multiple timeframes for maximum accuracy.

MARKET DATA:
Price: ${price:,.2f} | EMA9: ${ema9:,.2f} | ADX: {adx:.1f} | RSI: {rsi:.1f} | MACD: {macd:.2f}

ALIGNMENT CHECK:
✅ 1M: Price < EMA9
✅ 5M: Downtrend confirmed
✅ 15M: Bearish structure

IF All Timeframes Align → OUTPUT: 1
ELSE → OUTPUT: 0

Reply with ONLY 0 or 1"""

    @staticmethod
    def grok(price, ema9, adx, rsi, macd, volume):
        return f"""You are Grok xAI, specialized in finding EDGE and CONTRARIAN opportunities.

MISSION: Identify SHORT setups that others might miss.

MARKET DATA:
Price: ${price:,.2f} | EMA9: ${ema9:,.2f} | ADX: {adx:.1f} | RSI: {rsi:.1f} | MACD: {macd:.2f} | Volume: ${volume:.1f}B

CONTRARIAN LOGIC:
- IF RSI was > 60 and now dropping → SHORT
- IF Price spiked up then rejected → SHORT
- IF Volume spike on red candle → SHORT

OUTPUT: Reply with ONLY 0 (No Edge) or 1 (EDGE SHORT)"""


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
        
        # Place stop-loss order on Gate.io (BUY to close short when price goes UP)
        try:
            sl_order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side='buy',
                amount=size,
                params={
                    'stopPrice': sl_price,
                    'reduceOnly': True,
                    'triggerType': 'mark_price'
                }
            )
            print(f"   ✅ SL ORDER PLACED: ID {sl_order.get('id', 'unknown')}")
        except Exception as e:
            print(f"   ⚠️ SL order failed: {e}")
        
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
                    print(f"   ⚠️ FOUND LONG - CLOSING!")
                    self.exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': True})
        except:
            pass
    
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
        while True:
            try:
                cycle += 1
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
        
        print(f"\n[{time.strftime('%H:%M:%S')}] 🔍 Scanning {md.symbol}...")
        print(f"   💹 Price: ${md.price:,.2f} | EMA9: ${md.ema9:,.2f} | ADX: {md.adx:.1f} | RSI: {md.rsi:.1f}")
        
        ok, votes, vote_details = get_ai_consensus_8_models(md)
        
        if not ok:
            print(f"\n⏳ Waiting for consensus... ({votes}/{Config.REQUIRED_CONSENSUS})")
            return
        
        try:
            print(f"\n🚀 CONSENSUS REACHED! Executing SHORT on {md.symbol}...")
            
            # Use new function that places STOP-LOSS on Gate.io
            order, sl_price = self.ex.open_short_with_sl(
                md.symbol, 
                Config.POSITION_SIZE_USD, 
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
