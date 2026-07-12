#!/usr/bin/env python3
"""
====================================================================
AI MODELS TRADING RACE
SHORT-ONLY • GODS LEVEL • DAILY COMPETITION
====================================================================
"""
import os
import sys
import json
import time
import argparse
import ccxt
from datetime import datetime
from openai import OpenAI
from ai_race_scoring_engine import AIRaceScoringEngine, AIDailyStats, Trade
from GODS_LEVEL_PROMPTS import GodsLevelPrompts, MODEL_WEIGHTS

class Config:
    POSITION_SIZE_USD = 200.0
    LEVERAGE = 50
    SYMBOLS = ["ETH/USDT:USDT", "AVAX/USDT:USDT"]
    REQUIRED_CONSENSUS = 6
    CYCLE_SECONDS = 0.11  # TRIPLED SPEED (was 0.33)


class ChampionshipModel:
    def __init__(self, name, role, specialty):
        self.name = name
        self.role = role
        self.specialty = specialty
        self.wins = 0
        self.losses = 0
        self.no_trades = 0
        self.correct_no_trades = 0
        self.total_no_trades = 0
        self.pnl = 0.0
        self.max_drawdown = 0.0
        self.trades_list = []
        self.score = 0


class AIChampionship:
    def __init__(self, mode="dry"):
        self.mode = mode
        self.client = OpenAI()
        
        self.exchange = ccxt.gateio({
            'apiKey': os.getenv('GATE_API_KEY'),
            'secret': os.getenv('GATE_API_SECRET'),
            'options': {'defaultType': 'swap'}
        })
        
        self.models = [
            ChampionshipModel("DeepSeek", "MARKET PREDATOR", "Hunt fake pumps & distribution"),
            ChampionshipModel("GPT5", "ORDERBOOK GOD", "Order flow analysis"),
            ChampionshipModel("Claude", "RISK MONK", "Survival first, profit second"),
            ChampionshipModel("Llama", "SESSION MASTER", "Session-based trading"),
            ChampionshipModel("Gemini", "ADAPTIVE LEARNER", "Learn from experience"),
            ChampionshipModel("Mistral", "ANTI-TRAP SPECIALIST", "Detect traps & squeezes"),
            ChampionshipModel("Qwen", "CONFIDENCE SCORER", "Quality over quantity"),
            ChampionshipModel("Grok", "GODS LEVEL SYNTHESIZER", "Multiple factor alignment")
        ]
        
        self.trades = {}
        self.total_pnl = 0.0
        self.cycle = 0
        
        print("\n" + "="*70)
        print("🏆 AI WORLD SHORT-TRADING CHAMPIONSHIP")
        print("="*70)
        print(f"💰 Entry Size: ${Config.POSITION_SIZE_USD} @ {Config.LEVERAGE}x leverage")
        print(f"🤖 AI Models: 8 (Consensus: {Config.REQUIRED_CONSENSUS}/8)")
        print(f"⚡ Mode: {'🔴 LIVE TRADING' if mode == 'live' else '⚪ DRY RUN'}")
        print(f"📈 Pairs: {len(Config.SYMBOLS)}")
        print("="*70)
        print("⚠️  SHORT ONLY - LONGS FORBIDDEN")
        print("="*70 + "\n")
        
        # ENFORCE SHORTS ONLY - Close any existing LONGs
        if mode == 'live':
            self.close_all_longs()
    
    def close_all_longs(self):
        """SHORTS ONLY - Close ALL existing LONG positions"""
        print("\n🚨 SHORTS ONLY MODE - Checking for forbidden LONGs...")
        closed = 0
        try:
            for pos in self.exchange.fetch_positions():
                contracts = abs(float(pos.get('contracts', 0) or 0))
                side = pos.get('side')
                if contracts > 0 and side == 'long':
                    symbol = pos['symbol']
                    print(f"   ⚠️ CLOSING FORBIDDEN LONG: {symbol} ({contracts} contracts)")
                    self.exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': True})
                    closed += 1
        except Exception as e:
            print(f"   Error checking positions: {e}")
        
        if closed > 0:
            print(f"   ✅ Closed {closed} forbidden LONG position(s)")
        else:
            print("   ✅ No forbidden LONG positions found")
        print("")
    
    def get_market_data(self, symbol):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, '1m', limit=50)
            closes = [c[4] for c in ohlcv]
            volumes = [c[5] for c in ohlcv]
            
            price = closes[-1]
            ema9 = sum(closes[-9:]) / 9
            
            gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
            losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
            avg_gain = sum(gains[-14:]) / 14
            avg_loss = sum(losses[-14:]) / 14
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            ema12 = sum(closes[-12:]) / 12
            ema26 = sum(closes[-26:]) / 26
            macd = ema12 - ema26
            
            changes = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
            atr = sum(changes[-14:]) / 14 if len(changes) >= 14 else 0.01
            adx = min(50, max(15, rsi / 2 + 10))
            
            volume = sum(volumes[-5:]) / 5 * price / 1e9
            
            funding = 0
            try:
                fund = self.exchange.fetch_funding_rate(symbol)
                funding = float(fund.get('fundingRate', 0)) * 100
            except:
                pass
            
            return {
                'symbol': symbol,
                'price': price,
                'ema9': ema9,
                'adx': adx,
                'atr': atr,
                'rsi': rsi,
                'macd': macd,
                'volume': volume,
                'funding': funding
            }
        except Exception as e:
            print(f"Error getting market data: {e}")
            return None
    
    def build_prompt(self, model, market_data):
        """Build GODS LEVEL prompt for each AI model"""
        price = market_data['price']
        ema9 = market_data['ema9']
        rsi = market_data['rsi']
        macd = market_data['macd']
        funding = market_data['funding'] / 100
        adx = market_data['adx']
        atr = market_data['atr']
        volume = market_data['volume'] * 1e9
        
        prompts = GodsLevelPrompts()
        
        if model.name == "DeepSeek":
            return prompts.deepseek(price, ema9, rsi, macd, funding, adx, atr)
        elif model.name == "GPT5":
            return prompts.gpt5(price, ema9, rsi, macd, funding, volume, adx)
        elif model.name == "Claude":
            return prompts.claude(price, ema9, rsi, macd, funding, adx)
        elif model.name == "Llama":
            return prompts.llama(price, ema9, rsi, macd, funding, atr)
        elif model.name == "Gemini":
            return prompts.gemini(price, ema9, rsi, macd, funding, adx, volume)
        elif model.name == "Mistral":
            return prompts.mistral(price, ema9, rsi, macd, funding, adx)
        elif model.name == "Qwen":
            return prompts.qwen(price, ema9, rsi, macd, funding, adx, atr)
        elif model.name == "Grok":
            return prompts.grok(price, ema9, rsi, macd, funding, adx, volume)
        else:
            return prompts.deepseek(price, ema9, rsi, macd, funding, adx, atr)
    
    def query_model(self, model, market_data):
        """Query AI model with GODS LEVEL prompt"""
        try:
            prompt = self.build_prompt(model, market_data)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.2
            )
            
            reply = response.choices[0].message.content.strip()
            
            decision = "NO TRADE"
            confidence = 0
            weight = MODEL_WEIGHTS.get(model.name, 1.0)
            
            if '1' in reply and 'short' in reply.lower():
                decision = "SHORT"
                confidence = 85
            elif reply.strip() == '1':
                decision = "SHORT"
                confidence = 80
            elif 'short' in reply.lower():
                decision = "SHORT"
                confidence = 75
            elif reply.strip() == '0':
                decision = "NO TRADE"
                confidence = 0
            
            return {
                "decision": decision, 
                "confidence": confidence, 
                "weight": weight,
                "weighted_vote": weight if decision == "SHORT" else 0
            }
            
        except Exception as e:
            return {"decision": "NO TRADE", "confidence": 0, "weight": 1.0, "weighted_vote": 0}
    
    def get_all_decisions(self, market_data):
        """Get GODS LEVEL decisions from all 8 AI models with weighted voting"""
        rsi = market_data['rsi']
        rsi_zone = "🔴 OVERBOUGHT" if rsi > 70 else "⚠️ ELEVATED" if rsi > 60 else "⚪ NEUTRAL" if rsi > 40 else "🟢 OVERSOLD"
        
        print(f"\n🗳️  GODS LEVEL VOTING: {market_data['symbol']} | RSI: {rsi:.1f} {rsi_zone}")
        print("-" * 60)
        
        decisions = []
        short_votes = 0
        weighted_votes = 0.0
        total_weight = sum(MODEL_WEIGHTS.values())
        
        for model in self.models:
            result = self.query_model(model, market_data)
            result["model"] = model.name
            result["role"] = model.role
            decisions.append(result)
            
            weight = result.get("weight", 1.0)
            
            if result["decision"] == "SHORT":
                short_votes += 1
                weighted_votes += weight
                icon = "✅"
            else:
                icon = "❌"
            
            print(f"   {icon} [{model.name:8}] {result['decision']:8} | W:{weight:.1f}x | {result['confidence']}%")
        
        print("-" * 60)
        weighted_pct = (weighted_votes / total_weight) * 100
        print(f"📊 VOTES: {short_votes}/8 | WEIGHTED: {weighted_votes:.1f}/{total_weight:.1f} ({weighted_pct:.0f}%)")
        print(f"🎯 REQUIRED: {Config.REQUIRED_CONSENSUS}/8 votes OR 60% weighted")
        
        return decisions, short_votes, weighted_votes
    
    def execute_short(self, symbol, market_data, decisions):
        if self.mode != "live":
            print(f"\n⚪ [DRY RUN] Would open SHORT on {symbol}")
            return None
        
        try:
            self.exchange.set_leverage(Config.LEVERAGE, symbol)
        except:
            pass
        
        price = market_data['price']
        size = (Config.POSITION_SIZE_USD * Config.LEVERAGE) / price
        
        sl_pct = 0.02
        sl_price = round(price * (1 + sl_pct / 100), 4)
        tp_price = round(price * (1 - 0.01 / 100), 4)
        
        print(f"\n🚀 CHAMPIONSHIP TRADE EXECUTED!")
        print(f"   Symbol: {symbol}")
        print(f"   Direction: SHORT")
        print(f"   Entry: ${price:,.4f}")
        print(f"   Size: {size:.4f}")
        print(f"   Stop-Loss: ${sl_price}")
        print(f"   Take-Profit: ${tp_price}")
        
        order = self.exchange.create_market_sell_order(symbol, size, params={'reduceOnly': False})
        
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
            print(f"   ✅ SL ORDER PLACED")
        except Exception as e:
            print(f"   ⚠️ SL failed: {e}")
        
        self.trades[symbol] = {
            'entry': price,
            'size': size,
            'tp': tp_price,
            'sl': sl_price,
            'time': time.time(),
            'decisions': decisions
        }
        
        return order
    
    def manage_positions(self):
        for symbol in list(self.trades.keys()):
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = float(ticker['last'])
                trade = self.trades[symbol]
                
                pnl_pct = (trade['entry'] - current_price) / trade['entry']
                upnl = Config.POSITION_SIZE_USD * Config.LEVERAGE * pnl_pct
                
                if current_price <= trade['tp']:
                    print(f"\n🎯 TAKE PROFIT HIT on {symbol}! PnL: ${upnl:.2f}")
                    self.close_position(symbol, upnl)
                    del self.trades[symbol]
                elif current_price >= trade['sl']:
                    print(f"\n🛑 STOP LOSS HIT on {symbol}! PnL: ${upnl:.2f}")
                    self.close_position(symbol, upnl)
                    del self.trades[symbol]
                    
            except Exception as e:
                print(f"Error managing {symbol}: {e}")
    
    def close_position(self, symbol, pnl):
        if self.mode != "live":
            return
        
        try:
            for pos in self.exchange.fetch_positions([symbol]):
                contracts = abs(float(pos.get('contracts', 0) or 0))
                if contracts > 0:
                    self.exchange.create_market_buy_order(symbol, contracts, params={'reduceOnly': True})
                    self.total_pnl += pnl
                    
                    for order in self.exchange.fetch_open_orders(symbol):
                        try:
                            self.exchange.cancel_order(order['id'], symbol)
                        except:
                            pass
        except Exception as e:
            print(f"Error closing position: {e}")
    
    def update_leaderboard(self):
        scoring_engine = AIRaceScoringEngine()
        all_stats = []
        
        for model in self.models:
            stats = AIDailyStats(
                name=model.name,
                max_drawdown_percent=model.max_drawdown,
                correct_no_trade=model.correct_no_trades,
                total_no_trade=model.total_no_trades,
                trades=model.trades_list
            )
            model.score = scoring_engine.total_score(stats)
            all_stats.append(stats)
        
        data = {
            "race": "AI Models Trading Race",
            "last_updated": datetime.now().isoformat(),
            "total_cycles": self.cycle,
            "total_pnl": self.total_pnl,
            "models": {}
        }
        
        for model in self.models:
            data["models"][model.name] = {
                "role": model.role,
                "wins": model.wins,
                "losses": model.losses,
                "correct_no_trades": model.correct_no_trades,
                "total_no_trades": model.total_no_trades,
                "pnl": model.pnl,
                "max_drawdown": model.max_drawdown,
                "score": model.score
            }
        
        with open("leaderboard.json", "w") as f:
            json.dump(data, f, indent=2)
        
        scoring_engine.save_results(all_stats, "race_results.json")
    
    def print_leaderboard(self):
        sorted_models = sorted(self.models, key=lambda x: x.score, reverse=True)
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        
        print("\n" + "="*70)
        print("🏁 AI MODELS TRADING RACE - LEADERBOARD")
        print("="*70)
        
        for i, model in enumerate(sorted_models):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            print(f"\n{medal} {model.name} ({model.role})")
            print(f"   📊 Score: {model.score:.1f} points")
            print(f"   💰 PnL: ${model.pnl:.2f} | W:{model.wins} L:{model.losses}")
            print(f"   🧠 Correct NO TRADEs: {model.correct_no_trades}/{model.total_no_trades}")
        
        print("\n" + "="*70)
        if sorted_models:
            print(f"🏆 LEADER: {sorted_models[0].name} with {sorted_models[0].score:.1f} points!")
        print("="*70 + "\n")
    
    def run(self):
        print("\n🏁 CHAMPIONSHIP STARTED!\n")
        
        try:
            while True:
                self.cycle += 1
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 Cycle #{self.cycle}")
                
                self.manage_positions()
                
                for symbol in Config.SYMBOLS:
                    if symbol in self.trades:
                        continue
                    
                    market_data = self.get_market_data(symbol)
                    if not market_data:
                        continue
                    
                    if market_data['funding'] < 0:
                        print(f"   ⏳ {symbol}: Funding {market_data['funding']:+.4f}% (shorts pay) - Skip")
                        continue
                    
                    print(f"\n🔍 Analyzing {symbol}...")
                    print(f"   💹 Price: ${market_data['price']:,.4f} | RSI: {market_data['rsi']:.1f}")
                    
                    decisions, short_votes, weighted_votes = self.get_all_decisions(market_data)
                    
                    # Track NO TRADE decisions for discipline scoring
                    is_bad_market = market_data['rsi'] < 35 or market_data['rsi'] > 75
                    
                    for model in self.models:
                        for d in decisions:
                            if d["model"] == model.name:
                                if d["decision"] == "NO TRADE":
                                    model.total_no_trades += 1
                                    if is_bad_market:
                                        model.correct_no_trades += 1
                    
                    # GODS LEVEL: Accept trade if 6+ votes OR 60%+ weighted votes
                    total_weight = sum(MODEL_WEIGHTS.values())
                    weighted_pct = (weighted_votes / total_weight) * 100
                    consensus_reached = short_votes >= Config.REQUIRED_CONSENSUS or weighted_pct >= 60
                    
                    if consensus_reached:
                        print(f"   🔥 GODS LEVEL CONSENSUS REACHED!")
                        self.execute_short(symbol, market_data, decisions)
                        
                        for model in self.models:
                            for d in decisions:
                                if d["model"] == model.name and d["decision"] == "SHORT":
                                    model.score += 5
                    
                    time.sleep(0.1)
                
                if self.cycle % 30 == 0:
                    self.update_leaderboard()
                    self.print_leaderboard()
                
                time.sleep(Config.CYCLE_SECONDS)
                
        except KeyboardInterrupt:
            print("\n\n🏁 CHAMPIONSHIP PAUSED")
            self.update_leaderboard()
            self.print_leaderboard()


def main():
    parser = argparse.ArgumentParser(description="AI World Short-Trading Championship")
    parser.add_argument("--mode", choices=["dry", "live"], default="dry", help="Trading mode")
    args = parser.parse_args()
    
    championship = AIChampionship(mode=args.mode)
    championship.run()


if __name__ == "__main__":
    main()
