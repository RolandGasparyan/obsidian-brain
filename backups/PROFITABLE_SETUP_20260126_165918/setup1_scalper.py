"""⚡ SETUP 1: THE SCALPER'S DREAM - High-frequency micro-scalping"""
import os, time, ccxt
from openai import OpenAI

class Config:
    NAME = "Setup 1: The Scalper's Dream"
    EXCHANGE = "binance"
    SYMBOL = "BTC/USDT"
    TESTNET = False  # Set True to test without real money
    POSITION_SIZE_USD = 50.0
    LEVERAGE = 50
    TAKE_PROFIT_PERCENT = 0.02
    STOP_LOSS_PERCENT = 0.02
    MAX_TRADE_DURATION_SECONDS = 20
    EXECUTION_CYCLE_SECONDS = 1  # Very fast
    REQUIRED_CONSENSUS = 4  # Lower threshold for speed
    DAILY_LOSS_LIMIT_USD = -15.0
    MAX_CONSECUTIVE_LOSSES = 5

class Exchange:
    def __init__(self):
        self.exchange = getattr(ccxt, Config.EXCHANGE)({
            'apiKey': os.getenv('EXCHANGE_API_KEY'),
            'secret': os.getenv('EXCHANGE_API_SECRET'),
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        if Config.TESTNET:
            self.exchange.set_sandbox_mode(True)
    
    def get_price(self):
        return self.exchange.fetch_ticker(Config.SYMBOL)['last']
    
    def get_ohlcv(self, limit=20):
        return self.exchange.fetch_ohlcv(Config.SYMBOL, '1m', limit=limit)
    
    def open_short(self, amount):
        try:
            self.exchange.set_leverage(Config.LEVERAGE, Config.SYMBOL)
        except:
            pass
        price = self.get_price()
        qty = (amount * Config.LEVERAGE) / price
        return self.exchange.create_market_sell_order(Config.SYMBOL, qty)
    
    def close_short(self):
        positions = self.exchange.fetch_positions([Config.SYMBOL])
        for pos in positions:
            if pos['symbol'] == Config.SYMBOL and float(pos['contracts']) != 0:
                qty = abs(float(pos['contracts']))
                return self.exchange.create_market_buy_order(
                    Config.SYMBOL, qty, params={'reduceOnly': True}
                )

class MarketData:
    def __init__(self, price, ema9, momentum):
        self.price = price
        self.ema9 = ema9
        self.momentum = momentum

def get_market_data(exchange):
    try:
        ohlcv = exchange.get_ohlcv(20)
        closes = [c[4] for c in ohlcv]
        price = closes[-1]
        
        # EMA9 calculation
        multiplier = 2 / 10
        ema = closes[0]
        for p in closes[1:]:
            ema = (p - ema) * multiplier + ema
        
        # Momentum (5-period)
        momentum = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
        
        return MarketData(round(price, 2), round(ema, 2), round(momentum, 4))
    except Exception as e:
        print(f"Market data error: {e}")
        return None

def get_ai_consensus(md, required=4):
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        prompt = f"SHORT {Config.SYMBOL}? Price:${md.price} EMA9:${md.ema9} Mom:{md.momentum}. Reply with a number 0-8 for votes."
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5
        )
        votes = int(response.choices[0].message.content.strip())
        votes = max(0, min(8, votes))
        return votes >= required, votes
    except:
        # Fallback: simple technical analysis
        votes = 0
        if md.price < md.ema9:
            votes += 4
        if md.momentum < 0:
            votes += 4
        return votes >= required, votes

class ScalpersDream:
    def __init__(self):
        self.exchange = Exchange()
        self.trade = None
        self.total_pnl = 0.0
        self.trade_count = 0
        self.wins = 0
        self.losses = 0
        self.consecutive_losses = 0
        self.start_time = time.time()
        self.halted = False
    
    def run(self):
        print(f"{'='*60}")
        print(f"⚡ {Config.NAME}")
        print(f"{'='*60}")
        print(f"Pair: {Config.SYMBOL} | Size: ${Config.POSITION_SIZE_USD} | Leverage: {Config.LEVERAGE}x")
        print(f"TP: +{Config.TAKE_PROFIT_PERCENT}% | SL: -{Config.STOP_LOSS_PERCENT}% | Cycle: {Config.EXECUTION_CYCLE_SECONDS}s")
        print(f"{'='*60}\n")
        
        while True:
            try:
                if self.halted:
                    print(f"[{time.strftime('%H:%M:%S')}] ⛔ HALTED - Daily loss limit reached")
                    time.sleep(60)
                    continue
                
                md = get_market_data(self.exchange)
                if md is None:
                    time.sleep(5)
                    continue
                
                if self.trade:
                    self._manage_trade(md)
                else:
                    self._find_trade(md)
                
                time.sleep(Config.EXECUTION_CYCLE_SECONDS)
                
            except KeyboardInterrupt:
                print("\n⚠️ Stopping bot...")
                self._close_all_positions()
                self._print_summary()
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(10)
    
    def _find_trade(self, md):
        # Condition 1: Price below EMA9
        if md.price >= md.ema9:
            print(f"[{time.strftime('%H:%M:%S')}] ⏳ Waiting... Price ${md.price:,.2f} > EMA9 ${md.ema9:,.2f}")
            return
        
        # Condition 2: AI consensus
        approved, votes = get_ai_consensus(md, Config.REQUIRED_CONSENSUS)
        if not approved:
            print(f"[{time.strftime('%H:%M:%S')}] ⏳ AI: {votes}/8 votes (need {Config.REQUIRED_CONSENSUS})")
            return
        
        # Open short position
        try:
            self.exchange.open_short(Config.POSITION_SIZE_USD)
            self.trade = {
                'entry': md.price,
                'time': time.time(),
                'tp': md.price * (1 - Config.TAKE_PROFIT_PERCENT / 100),
                'sl': md.price * (1 + Config.STOP_LOSS_PERCENT / 100)
            }
            self.trade_count += 1
            
            expected_profit = Config.POSITION_SIZE_USD * Config.LEVERAGE * Config.TAKE_PROFIT_PERCENT / 100
            print(f"\n[{time.strftime('%H:%M:%S')}] ⚡ SCALP SHORT #{self.trade_count}")
            print(f"   Entry: ${md.price:,.2f} | AI: {votes}/8")
            print(f"   TP: ${self.trade['tp']:,.2f} | SL: ${self.trade['sl']:,.2f}")
            print(f"   Expected: +${expected_profit:.2f}\n")
            
        except Exception as e:
            print(f"Order Error: {e}")
    
    def _manage_trade(self, md):
        t = self.trade
        elapsed = time.time() - t['time']
        pnl_percent = (t['entry'] - md.price) / t['entry']
        unrealized_pnl = Config.POSITION_SIZE_USD * Config.LEVERAGE * pnl_percent
        
        # Check TP
        if md.price <= t['tp']:
            self._close_trade(md, "🎯 TAKE PROFIT", True)
            return
        
        # Check SL
        if md.price >= t['sl']:
            self._close_trade(md, "🛑 STOP LOSS", False)
            return
        
        # Check time decay
        if elapsed >= Config.MAX_TRADE_DURATION_SECONDS:
            self._close_trade(md, "⏱️ TIME EXIT", unrealized_pnl > 0)
            return
        
        # Status update
        emoji = "📈" if unrealized_pnl > 0 else "📉"
        print(f"[{time.strftime('%H:%M:%S')}] {emoji} #{self.trade_count} | uPNL: ${unrealized_pnl:+.2f} | {elapsed:.0f}s")
    
    def _close_trade(self, md, reason, won):
        try:
            self.exchange.close_short()
        except Exception as e:
            print(f"Close error: {e}")
        
        pnl_percent = (self.trade['entry'] - md.price) / self.trade['entry']
        pnl = Config.POSITION_SIZE_USD * Config.LEVERAGE * pnl_percent
        self.total_pnl += pnl
        
        if won:
            self.wins += 1
            self.consecutive_losses = 0
        else:
            self.losses += 1
            self.consecutive_losses += 1
            if self.consecutive_losses >= Config.MAX_CONSECUTIVE_LOSSES:
                print(f"   ⚠️ {Config.MAX_CONSECUTIVE_LOSSES} consecutive losses - cooling down 30s")
                time.sleep(30)
                self.consecutive_losses = 0
        
        # Check daily loss limit
        if self.total_pnl <= Config.DAILY_LOSS_LIMIT_USD:
            self.halted = True
        
        mins = max(0.1, (time.time() - self.start_time) / 60)
        win_rate = self.wins / self.trade_count * 100 if self.trade_count > 0 else 0
        
        print(f"\n[{time.strftime('%H:%M:%S')}] {'💰' if won else '🔴'} {reason}")
        print(f"   PNL: ${pnl:+.2f} | Total: ${self.total_pnl:+.2f}")
        print(f"   WR: {win_rate:.0f}% | $/min: ${self.total_pnl/mins:+.2f}\n")
        
        self.trade = None
    
    def _close_all_positions(self):
        try:
            self.exchange.close_short()
        except:
            pass
    
    def _print_summary(self):
        mins = max(0.1, (time.time() - self.start_time) / 60)
        win_rate = self.wins / self.trade_count * 100 if self.trade_count > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"📊 FINAL SUMMARY - {Config.NAME}")
        print(f"{'='*60}")
        print(f"Total Trades: {self.trade_count}")
        print(f"Wins: {self.wins} | Losses: {self.losses}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Total PNL: ${self.total_pnl:+.2f}")
        print(f"$/minute: ${self.total_pnl/mins:+.2f}")
        print(f"Runtime: {mins:.1f} minutes")
        print(f"{'='*60}")

if __name__ == "__main__":
    ScalpersDream().run()
