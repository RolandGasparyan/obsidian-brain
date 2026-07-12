# ============================================================================
# 🎯 SETUP 2: THE SNIPER'S PATIENCE
# ============================================================================
# Low-frequency, high R:R | 4:1 R:R | Slow (5s cycles)
# Goal: $1 USDT per minute through quality trades
# ============================================================================

# STEP 1: Install dependencies
pip install ccxt python-dotenv openai

# STEP 2: Create the bot (copy this entire block)
cat > /home/runner/workspace/setup2_sniper.py << 'EOF'
"""
🎯 SETUP 2: THE SNIPER'S PATIENCE
Low-frequency, high R:R trading
Target: $1 USDT per minute through quality
"""
import os
import time
import ccxt
from openai import OpenAI

# ============================================================================
# CONFIGURATION
# ============================================================================
class Config:
    NAME = "Setup 2: The Sniper's Patience"

    # Exchange Settings
    EXCHANGE = "binance"
    SYMBOL = "BTC/USDT"
    TESTNET = False  # SET TO TRUE FOR TESTING FIRST

    # Position Settings (larger for bigger wins)
    POSITION_SIZE_USD = 100.0
    LEVERAGE = 50

    # Take Profit / Stop Loss (4:1 R:R)
    TAKE_PROFIT_PERCENT = 0.08  # +$4.00 profit
    STOP_LOSS_PERCENT = 0.02   # -$1.00 loss

    # Timing (slower, more patient)
    MAX_TRADE_DURATION_SECONDS = 60
    EXECUTION_CYCLE_SECONDS = 5

    # AI Consensus (strict for quality)
    REQUIRED_CONSENSUS = 6  # 6/8 models

    # Risk Management (tight)
    DAILY_LOSS_LIMIT_USD = -15.0
    MAX_CONSECUTIVE_LOSSES = 2
    COOLDOWN_SECONDS = 60

# ============================================================================
# EXCHANGE CONNECTOR
# ============================================================================
class Exchange:
    def __init__(self):
        api_key = os.getenv('EXCHANGE_API_KEY')
        api_secret = os.getenv('EXCHANGE_API_SECRET')

        if not api_key or not api_secret:
            raise ValueError("Set EXCHANGE_API_KEY and EXCHANGE_API_SECRET in Replit Secrets")

        self.exchange = getattr(ccxt, Config.EXCHANGE)({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })

        if Config.TESTNET:
            self.exchange.set_sandbox_mode(True)
            print("⚠️ TESTNET MODE ENABLED")

    def get_price(self):
        ticker = self.exchange.fetch_ticker(Config.SYMBOL)
        return ticker['last']

    def get_ohlcv(self, limit=50):
        return self.exchange.fetch_ohlcv(Config.SYMBOL, '1m', limit=limit)

    def open_short(self, amount_usdt):
        try:
            self.exchange.set_leverage(Config.LEVERAGE, Config.SYMBOL)
        except:
            pass
        price = self.get_price()
        amount = (amount_usdt * Config.LEVERAGE) / price
        return self.exchange.create_market_sell_order(Config.SYMBOL, amount)

    def close_short(self):
        positions = self.exchange.fetch_positions([Config.SYMBOL])
        for pos in positions:
            if pos['symbol'] == Config.SYMBOL and float(pos['contracts']) != 0:
                amount = abs(float(pos['contracts']))
                return self.exchange.create_market_buy_order(
                    Config.SYMBOL, amount, params={'reduceOnly': True}
                )
        return None

# ============================================================================
# MARKET DATA
# ============================================================================
class MarketData:
    def __init__(self, price, ema9, ema20, rsi, momentum):
        self.price = price
        self.ema9 = ema9
        self.ema20 = ema20
        self.rsi = rsi
        self.momentum = momentum

def get_market_data(exchange):
    try:
        ohlcv = exchange.get_ohlcv(30)
        closes = [c[4] for c in ohlcv]
        price = closes[-1]

        # EMA9
        m9 = 2 / 10
        ema9 = closes[0]
        for p in closes[1:]:
            ema9 = (p - ema9) * m9 + ema9

        # EMA20
        m20 = 2 / 21
        ema20 = closes[0]
        for p in closes[1:]:
            ema20 = (p - ema20) * m20 + ema20

        # RSI
        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(0, change))
            losses.append(abs(min(0, change)))
        avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else 0.001
        avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else 0.001
        rs = avg_gain / avg_loss if avg_loss > 0 else 1
        rsi = 100 - (100 / (1 + rs))

        # Momentum
        momentum = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0

        return MarketData(round(price, 2), round(ema9, 2), round(ema20, 2), round(rsi, 1), round(momentum, 4))
    except Exception as e:
        print(f"Data Error: {e}")
        return None

# ============================================================================
# AI CONSENSUS
# ============================================================================
def get_ai_consensus(md, required=6):
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        prompt = f"""Analyze SHORT for {Config.SYMBOL}:
Price: ${md.price:,.2f} | EMA9: ${md.ema9:,.2f} | EMA20: ${md.ema20:,.2f}
RSI: {md.rsi} | Momentum: {md.momentum:.4f}

From 8 perspectives (Quant, Macro, Contrarian, Scalper, Analyst, Risk, Pattern, News), how many would APPROVE a SHORT? Reply with just a number 0-8."""

        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0.3
        )
        votes = int(response.choices[0].message.content.strip())
        votes = max(0, min(8, votes))
        return votes >= required, votes
    except Exception as e:
        # Fallback
        votes = 0
        if md.price < md.ema9: votes += 2
        if md.ema9 < md.ema20: votes += 2
        if md.rsi > 55: votes += 2
        if md.momentum < 0: votes += 2
        return votes >= required, votes

# ============================================================================
# TRADING ENGINE
# ============================================================================
class SnipersPatience:
    def __init__(self):
        self.exchange = Exchange()
        self.trade = None
        self.total_pnl = 0.0
        self.trade_count = 0
        self.wins = 0
        self.losses = 0
        self.consecutive_losses = 0
        self.start_time = None
        self.halted = False

    def run(self):
        self.start_time = time.time()
        self._header()

        while True:
            try:
                if self.halted:
                    print(f"[{self._t()}] 🛑 HALTED - Daily loss limit reached")
                    time.sleep(60)
                    continue

                md = get_market_data(self.exchange)
                if md is None:
                    time.sleep(5)
                    continue

                if self.trade:
                    self._manage(md)
                else:
                    self._find(md)

                time.sleep(Config.EXECUTION_CYCLE_SECONDS)
            except KeyboardInterrupt:
                self._close_all()
                self._summary()
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(10)

    def _header(self):
        print("=" * 60)
        print(f"🎯 {Config.NAME}")
        print("=" * 60)
        print(f"Exchange: {Config.EXCHANGE} | Testnet: {Config.TESTNET}")
        print(f"Symbol: {Config.SYMBOL} | Leverage: {Config.LEVERAGE}x")
        print(f"Position: ${Config.POSITION_SIZE_USD} | TP: +{Config.TAKE_PROFIT_PERCENT}% | SL: -{Config.STOP_LOSS_PERCENT}%")
        print(f"R:R = 4:1 | AI Consensus: {Config.REQUIRED_CONSENSUS}/8 (STRICT)")
        print("=" * 60)
        print("")

    def _t(self):
        return time.strftime('%H:%M:%S')

    def _find(self, md):
        # STRICT Entry conditions
        if md.price >= md.ema9:
            self._wait(md, "Price > EMA9")
            return
        if md.ema9 >= md.ema20:
            self._wait(md, "EMA9 > EMA20")
            return
        if md.rsi < 55:
            self._wait(md, f"RSI {md.rsi} < 55")
            return

        # AI consensus (strict)
        approved, votes = get_ai_consensus(md, Config.REQUIRED_CONSENSUS)
        if not approved:
            self._wait(md, f"AI: {votes}/8 (need {Config.REQUIRED_CONSENSUS})")
            return

        # EXECUTE SHORT
        try:
            self.exchange.open_short(Config.POSITION_SIZE_USD)
            self.trade = {
                'entry': md.price,
                'time': time.time(),
                'tp': md.price * (1 - Config.TAKE_PROFIT_PERCENT / 100),
                'sl': md.price * (1 + Config.STOP_LOSS_PERCENT / 100),
            }
            self.trade_count += 1
            exp = Config.POSITION_SIZE_USD * Config.LEVERAGE * Config.TAKE_PROFIT_PERCENT / 100
            print(f"\n[{self._t()}] 🎯 SNIPER SHORT #{self.trade_count}")
            print(f"   Entry: ${md.price:,.2f} | TP: ${self.trade['tp']:,.2f} | SL: ${self.trade['sl']:,.2f}")
            print(f"   AI: {votes}/8 | RSI: {md.rsi} | Expected: +${exp:.2f}")
        except Exception as e:
            print(f"Order Error: {e}")

    def _manage(self, md):
        t = self.trade
        elapsed = time.time() - t['time']
        pnl_pct = (t['entry'] - md.price) / t['entry']
        upnl = Config.POSITION_SIZE_USD * Config.LEVERAGE * pnl_pct

        if md.price <= t['tp']:
            self._close(md, "🎯 TP HIT (+4R)", True)
        elif md.price >= t['sl']:
            self._close(md, "🛑 SL HIT (-1R)", False)
        elif elapsed >= Config.MAX_TRADE_DURATION_SECONDS:
            self._close(md, f"⏱️ TIME ({elapsed:.0f}s)", upnl > 0)
        else:
            e = "📈" if upnl > 0 else "📉"
            print(f"[{self._t()}] {e} #{self.trade_count} | ${md.price:,.2f} | uPNL: ${upnl:+.2f} | {elapsed:.0f}s")

    def _close(self, md, reason, won):
        try:
            self.exchange.close_short()
        except Exception as e:
            print(f"Close Error: {e}")

        t = self.trade
        pnl_pct = (t['entry'] - md.price) / t['entry']
        pnl = Config.POSITION_SIZE_USD * Config.LEVERAGE * pnl_pct
        self.total_pnl += pnl

        if won:
            self.wins += 1
            self.consecutive_losses = 0
        else:
            self.losses += 1
            self.consecutive_losses += 1
            if self.consecutive_losses >= Config.MAX_CONSECUTIVE_LOSSES:
                print(f"   ⚠️ {Config.MAX_CONSECUTIVE_LOSSES} losses - cooling {Config.COOLDOWN_SECONDS}s")
                time.sleep(Config.COOLDOWN_SECONDS)
                self.consecutive_losses = 0

        if self.total_pnl <= Config.DAILY_LOSS_LIMIT_USD:
            self.halted = True

        mins = max(0.1, (time.time() - self.start_time) / 60)
        ppm = self.total_pnl / mins
        wr = self.wins / self.trade_count * 100 if self.trade_count > 0 else 0

        emoji = "💰" if won else "🔴"
        print(f"\n[{self._t()}] {emoji} {reason}")
        print(f"   PNL: ${pnl:+.2f} | Total: ${self.total_pnl:+.2f} | WR: {wr:.0f}%")
        print(f"   $/min: ${ppm:+.2f} | Trades: {self.trade_count}")
        print("")

        self.trade = None

    def _wait(self, md, reason):
        mins = max(0.1, (time.time() - self.start_time) / 60)
        ppm = self.total_pnl / mins if self.start_time else 0
        print(f"[{self._t()}] ⏳ {reason} | ${md.price:,.2f} | ${ppm:+.2f}/min")

    def _close_all(self):
        try:
            self.exchange.close_short()
        except:
            pass

    def _summary(self):
        mins = max(0.1, (time.time() - self.start_time) / 60)
        wr = self.wins / self.trade_count * 100 if self.trade_count > 0 else 0
        print(f"\n{'='*60}")
        print(f"📊 FINAL SUMMARY - {Config.NAME}")
        print(f"{'='*60}")
        print(f"Trades: {self.trade_count} | Wins: {self.wins} | Losses: {self.losses}")
        print(f"Win Rate: {wr:.1f}%")
        print(f"Total PNL: ${self.total_pnl:+.2f}")
        print(f"$/min: ${self.total_pnl/mins:+.2f}")
        print(f"{'='*60}")

# ============================================================================
# RUN
# ============================================================================
if __name__ == "__main__":
    SnipersPatience().run()
EOF
echo "✅ Setup 2: The Sniper's Patience created"

# STEP 3: Run the bot
python /home/runner/workspace/setup2_sniper.py
