"""
📈 SETUP 3: THE TREND RIDER
ADX-based trend following with trailing stop
"""
import os, time, ccxt
from openai import OpenAI

class Config:
    NAME = "Setup 3: The Trend Rider"
    EXCHANGE = "binance"
    SYMBOL = "BTC/USDT"
    TESTNET = False
    POSITION_SIZE_USD = 75.0
    LEVERAGE = 50
    TAKE_PROFIT_PERCENT = 0.05
    STOP_LOSS_PERCENT = 0.025
    TRAILING_STOP_PERCENT = 0.03
    MAX_TRADE_DURATION_SECONDS = 120
    EXECUTION_CYCLE_SECONDS = 3
    REQUIRED_CONSENSUS = 5
    MIN_ADX = 30
    DAILY_LOSS_LIMIT_USD = -20.0
    MAX_CONSECUTIVE_LOSSES = 3

class Exchange:
    def __init__(self):
        self.exchange = getattr(ccxt, Config.EXCHANGE)({
            'apiKey': os.getenv('EXCHANGE_API_KEY'),
            'secret': os.getenv('EXCHANGE_API_SECRET'),
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        if Config.TESTNET: self.exchange.set_sandbox_mode(True)
    
    def get_ohlcv(self, limit=50):
        return self.exchange.fetch_ohlcv(Config.SYMBOL, '1m', limit=limit)
    
    def open_short(self, amount):
        try: self.exchange.set_leverage(Config.LEVERAGE, Config.SYMBOL)
        except: pass
        price = self.exchange.fetch_ticker(Config.SYMBOL)['last']
        return self.exchange.create_market_sell_order(Config.SYMBOL, (amount * Config.LEVERAGE) / price)
    
    def close_short(self):
        for pos in self.exchange.fetch_positions([Config.SYMBOL]):
            if pos['symbol'] == Config.SYMBOL and float(pos['contracts']) != 0:
                return self.exchange.create_market_buy_order(Config.SYMBOL, abs(float(pos['contracts'])), params={'reduceOnly': True})

class MarketData:
    def __init__(self, price, ema9, adx, momentum):
        self.price, self.ema9, self.adx, self.momentum = price, ema9, adx, momentum

def get_market_data(exchange):
    try:
        ohlcv = exchange.get_ohlcv(30)
        closes = [c[4] for c in ohlcv]
        price = closes[-1]
        m = 2/10
        ema = closes[0]
        for p in closes[1:]: ema = (p-ema)*m + ema
        changes = [closes[i]-closes[i-1] for i in range(1, len(closes))]
        pos = sum(max(0,c) for c in changes[-14:])
        neg = sum(abs(min(0,c)) for c in changes[-14:])
        adx = abs(pos-neg)/(pos+neg)*100 if pos+neg > 0 else 25
        momentum = (closes[-1]-closes[-5])/closes[-5] if len(closes)>=5 else 0
        return MarketData(round(price,2), round(ema,2), round(adx,1), round(momentum,4))
    except: return None

def get_ai_consensus(md, required=5):
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        r = client.chat.completions.create(model="gpt-4.1-nano", messages=[{"role":"user","content":f"SHORT {Config.SYMBOL}? Price:${md.price} EMA9:${md.ema9} ADX:{md.adx} Mom:{md.momentum}. Reply 0-8 votes."}], max_tokens=5)
        votes = max(0, min(8, int(r.choices[0].message.content.strip())))
        return votes >= required, votes
    except:
        votes = (3 if md.price < md.ema9 else 0) + (3 if md.adx > 30 else 0) + (2 if md.momentum < 0 else 0)
        return votes >= required, votes

class TrendRider:
    def __init__(self):
        self.exchange = Exchange()
        self.trade = None
        self.total_pnl = 0.0
        self.trade_count = self.wins = self.losses = 0
        self.start_time = time.time()
        self.halted = False
    
    def run(self):
        print(f"{'='*60}\n📈 {Config.NAME}\n{'='*60}")
        print(f"ADX Filter: > {Config.MIN_ADX} | Trailing: {Config.TRAILING_STOP_PERCENT}%\n")
        while True:
            try:
                if self.halted: time.sleep(60); continue
                md = get_market_data(self.exchange)
                if md: self._manage(md) if self.trade else self._find(md)
                time.sleep(Config.EXECUTION_CYCLE_SECONDS)
            except KeyboardInterrupt:
                self._close_all(); self._summary(); break
            except Exception as e: print(f"Error: {e}"); time.sleep(10)
    
    def _find(self, md):
        if md.adx < Config.MIN_ADX: print(f"[{time.strftime('%H:%M:%S')}] ⏳ ADX:{md.adx} < {Config.MIN_ADX}"); return
        if md.price >= md.ema9: print(f"[{time.strftime('%H:%M:%S')}] ⏳ Price > EMA9"); return
        approved, votes = get_ai_consensus(md)
        if not approved: print(f"[{time.strftime('%H:%M:%S')}] ⏳ AI:{votes}/8"); return
        try:
            self.exchange.open_short(Config.POSITION_SIZE_USD)
            self.trade = {'entry': md.price, 'time': time.time(), 'tp': md.price*(1-Config.TAKE_PROFIT_PERCENT/100), 'sl': md.price*(1+Config.STOP_LOSS_PERCENT/100), 'lowest': md.price, 'trailing': False}
            self.trade_count += 1
            print(f"\n[{time.strftime('%H:%M:%S')}] 📈 TREND SHORT #{self.trade_count} | Entry:${md.price:,.2f} | ADX:{md.adx}")
        except Exception as e: print(f"Order Error: {e}")
    
    def _manage(self, md):
        t = self.trade
        elapsed = time.time() - t['time']
        pnl_pct = (t['entry']-md.price)/t['entry']
        upnl = Config.POSITION_SIZE_USD * Config.LEVERAGE * pnl_pct
        if md.price < t['lowest']:
            t['lowest'] = md.price
            if pnl_pct > 0.01: t['trailing'] = True; t['sl'] = md.price*(1+Config.TRAILING_STOP_PERCENT/100)
        if md.price <= t['tp']: self._close(md, "🎯 TP", True)
        elif md.price >= t['sl']: self._close(md, "🔒 TRAIL" if t['trailing'] else "🛑 SL", upnl > 0)
        elif elapsed >= Config.MAX_TRADE_DURATION_SECONDS: self._close(md, "⏱️ TIME", upnl > 0)
        else: print(f"[{time.strftime('%H:%M:%S')}] {'🔒' if t['trailing'] else '📊'} uPNL:${upnl:+.2f}")
    
    def _close(self, md, reason, won):
        try: self.exchange.close_short()
        except: pass
        pnl = Config.POSITION_SIZE_USD * Config.LEVERAGE * (self.trade['entry']-md.price)/self.trade['entry']
        self.total_pnl += pnl
        if won: self.wins += 1
        else: self.losses += 1
        if self.total_pnl <= Config.DAILY_LOSS_LIMIT_USD: self.halted = True
        mins = max(0.1, (time.time()-self.start_time)/60)
        print(f"\n[{time.strftime('%H:%M:%S')}] {'💰' if won else '🔴'} {reason} | PNL:${pnl:+.2f} | Total:${self.total_pnl:+.2f} | $/min:${self.total_pnl/mins:+.2f}\n")
        self.trade = None
    
    def _close_all(self):
        try: self.exchange.close_short()
        except: pass
    
    def _summary(self):
        mins = max(0.1, (time.time()-self.start_time)/60)
        wr = self.wins/self.trade_count*100 if self.trade_count else 0
        print(f"\n{'='*60}\n📊 SUMMARY: {self.trade_count} trades | {self.wins}W/{self.losses}L | WR:{wr:.0f}% | ${self.total_pnl:+.2f} | ${self.total_pnl/mins:+.2f}/min\n{'='*60}")

if __name__ == "__main__": TrendRider().run()
