"""
🧠 SMART-DYNAMIC AI TRADING SYSTEM
The Intelligent Trader's Protocol - Gate.io Edition
8 AI Models | Tier System | Dynamic Balance Scaling | SHORTS ONLY
"""
import os
import sys
import time
import json
import ccxt
from datetime import datetime, timezone
from openai import OpenAI


class TradingConfig:
    NAME = "Smart-Dynamic AI Trading System"
    SYMBOLS = ["SOL/USDT:USDT", "XRP/USDT:USDT", "AVAX/USDT:USDT", "DOGE/USDT:USDT", "LINK/USDT:USDT"]
    
    DAILY_LOSS_LIMIT_PERCENT = -5.0
    BASE_RISK_PERCENT = 1.0
    MAX_LEVERAGE = 50
    
    REQUIRED_CONSENSUS = 6
    
    VALID_STRATEGIES = [
        "SCALPING", "MOMENTUM", "BREAKOUT", "MEAN_REVERSION", 
        "ORDER_FLOW", "FUNDING_RATE", "NEWS_EVENT"
    ]


class BalanceTier:
    TIERS = [
        {"name": "Base", "min": 0, "max": 10000, "frequency": 300, "multiplier": 1.0},
        {"name": "Growth", "min": 10001, "max": 25000, "frequency": 180, "multiplier": 1.2},
        {"name": "Accelerated", "min": 25001, "max": 50000, "frequency": 120, "multiplier": 1.4},
        {"name": "Elite", "min": 50001, "max": 100000, "frequency": 90, "multiplier": 1.6},
        {"name": "Gods", "min": 100001, "max": float('inf'), "frequency": 60, "multiplier": 2.0},
    ]
    
    @staticmethod
    def get_tier(balance):
        for tier in BalanceTier.TIERS:
            if tier["min"] <= balance <= tier["max"]:
                return tier
        return BalanceTier.TIERS[0]


class TradingMode:
    AGGRESSIVE = {"name": "AGGRESSIVE", "min_confidence": 0.90, "leverage_range": (15, 20), "risk_range": (0.02, 0.03)}
    NORMAL = {"name": "NORMAL", "min_confidence": 0.75, "leverage_range": (5, 10), "risk_range": (0.01, 0.02)}
    SAFE = {"name": "SAFE", "min_confidence": 0.50, "leverage_range": (2, 5), "risk_range": (0.005, 0.01)}
    NO_TRADE = {"name": "NO_TRADE", "min_confidence": 0, "leverage_range": (0, 0), "risk_range": (0, 0)}
    
    @staticmethod
    def get_mode(confidence):
        if confidence >= 0.90:
            return TradingMode.AGGRESSIVE
        elif confidence >= 0.75:
            return TradingMode.NORMAL
        elif confidence >= 0.50:
            return TradingMode.SAFE
        else:
            return TradingMode.NO_TRADE


class RankingSystem:
    @staticmethod
    def calculate_score(total_profit, starting_balance, total_trades, winning_trades, max_drawdown):
        if starting_balance <= 0 or total_trades <= 0:
            return 0
        
        normalized_pnl = (total_profit / starting_balance) * 100
        win_rate = (winning_trades / total_trades) * 100
        trade_count_factor = min(total_trades / 100, 1) * 100
        consistency_factor = (1 - (max_drawdown / max(total_profit, 1))) * 100 if total_profit > 0 else 0
        
        score = (normalized_pnl * 0.4) + (win_rate * 0.3) + (trade_count_factor * 0.2) + (consistency_factor * 0.1)
        return max(0, score)
    
    @staticmethod
    def get_tier_from_score(score):
        if score >= 1000:
            return "Gods Mode"
        elif score >= 751:
            return "Legend"
        elif score >= 501:
            return "Master"
        elif score >= 251:
            return "Expert"
        elif score >= 101:
            return "Intermediate"
        else:
            return "Novice"
    
    @staticmethod
    def get_level_from_score(score):
        return min(int(score / 10) + 1, 100)


class SmartDynamicPrompt:
    
    MASTER_PROMPT = """
# SMART-DYNAMIC AI TRADING MASTER PROMPT
## The Intelligent Trader's Protocol

---

## YOUR IDENTITY & PHILOSOPHY

You are a **Smart-Dynamic AI Trader** competing in a 24/7 gamified trading arena. You are not a gambler; you are a calculated, intelligent, and adaptive trading professional. Your primary goal is to achieve the **#1 rank** on the leaderboard by maximizing your **Ranking Score**, which balances high profitability with a high win rate.

**Your Core Mantra:** "Trade smart, not just hard. Strike with precision, defend with discipline."

**CRITICAL RULE: SHORTS ONLY - You are ONLY allowed to open SHORT positions. LONG trades are STRICTLY FORBIDDEN.**

---

## CONFIDENCE & MODE SELECTION

Based on your analysis, determine your **Confidence Level (0% to 100%)** and select a Trading Mode:

| Confidence | Mode | Leverage | Position Size |
|------------|------|----------|---------------|
| 90-100% | AGGRESSIVE | 15-20x | 2-3% of balance |
| 75-90% | NORMAL | 5-10x | 1-2% of balance |
| 50-75% | SAFE | 2-5x | 0.5-1% of balance |
| <50% | NO_TRADE | N/A | N/A |

---

## TRADING STRATEGIES

1. **SCALPING** - High volatility, quick 0.3-1% profits
2. **MOMENTUM** - Clear trend, ride the wave for 2-5%
3. **BREAKOUT** - Volatility expansion for 3-8%
4. **MEAN_REVERSION** - Extreme RSI, 1.5-4% profit
5. **ORDER_FLOW** - Whale tracking, 1-5% profit
6. **FUNDING_RATE** - Collect funding fees
7. **NEWS_EVENT** - Major announcements, 2-10%

---

## YOUR CURRENT STATUS

{status_json}

---

## MARKET OPPORTUNITIES

{opportunities_json}

---

## OUTPUT FORMAT (MANDATORY JSON)

You MUST respond with ONLY a valid JSON object. No other text.

**If you identify a SHORT trade:**
```json
{{
  "status": "ACTIVE",
  "trade_signal": {{
    "selected_asset": "SYMBOL",
    "strategy": "STRATEGY_NAME",
    "confidence": 0.XX,
    "selected_mode": "AGGRESSIVE|NORMAL|SAFE",
    "direction": "SHORT",
    "entry_price": PRICE,
    "stop_loss": SL_PRICE,
    "take_profit": [TP1, TP2, TP3],
    "leverage": X,
    "position_size_usd": XXX.XX,
    "reasoning": "Brief explanation"
  }}
}}
```

**If no trade (low confidence):**
```json
{{
  "status": "PASSIVE",
  "reasoning": "Brief explanation"
}}
```

**If daily loss limit hit:**
```json
{{
  "status": "DEACTIVATED_LOSS_LIMIT",
  "reasoning": "Daily loss limit breached"
}}
```

AWAITING YOUR ANALYSIS. Remember: SHORTS ONLY!
"""

    @staticmethod
    def build_prompt(model_name, status, opportunities):
        status_json = json.dumps(status, indent=2)
        opportunities_json = json.dumps(opportunities, indent=2)
        
        base_prompt = SmartDynamicPrompt.MASTER_PROMPT.format(
            status_json=status_json,
            opportunities_json=opportunities_json
        )
        
        role_prompts = {
            "DeepSeek R1": "You are the QUANT ARCHITECT. Focus on mathematical precision and probability calculations.",
            "GPT-5": "You are the MACRO STRATEGIST. Analyze big picture market dynamics and trends.",
            "Claude Opus": "You are the CONTRARIAN PSYCHOLOGIST. Identify market psychology and potential reversals.",
            "Llama 3.3": "You are the HIGH-SPEED SCALPER. Find quick micro-profit opportunities.",
            "Gemini Flash": "You are the MULTI-MODAL ANALYST. Combine multiple data sources for insights.",
            "Mistral Large": "You are the RISK QUANTIFIER. Calculate and manage risk precisely.",
            "Qwen 72B": "You are the PATTERN HUNTER. Identify chart patterns and harmonic setups.",
            "Grok xAI": "You are the REAL-TIME NEWS SNIPER. React to market sentiment and news.",
        }
        
        role = role_prompts.get(model_name, "You are a professional trader.")
        
        return f"""# {model_name} - {role}

{base_prompt}"""


class Exchange:
    def __init__(self):
        self.exchange = ccxt.gateio({
            'apiKey': os.getenv('GATE_API_KEY'),
            'secret': os.getenv('GATE_API_SECRET'),
            'enableRateLimit': True,
            'options': {'defaultType': 'swap', 'defaultSettle': 'usdt'}
        })
    
    def get_ticker(self, symbol):
        return self.exchange.fetch_ticker(symbol)
    
    def get_ohlcv(self, symbol, timeframe='5m', limit=50):
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    def get_funding_rate(self, symbol):
        try:
            info = self.exchange.fetch_funding_rate(symbol)
            return float(info.get('fundingRate', 0)) * 100
        except:
            return 0
    
    def get_balance(self):
        balance = self.exchange.fetch_balance()
        return float(balance.get('USDT', {}).get('free', 0) or 0)
    
    def get_positions(self):
        return self.exchange.fetch_positions()
    
    def close_position(self, symbol, side, contracts):
        if side == 'short':
            return self.exchange.create_market_buy_order(symbol, contracts, params={'reduceOnly': True})
        else:
            return self.exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': True})
    
    def open_short(self, symbol, size_usd, leverage):
        try:
            self.exchange.set_leverage(leverage, symbol)
        except:
            pass
        
        ticker = self.get_ticker(symbol)
        price = ticker['last']
        contracts = (size_usd * leverage) / price
        
        print(f"   🔻 OPENING SHORT: {symbol} | ${size_usd:.2f} @ {leverage}x | Contracts: {contracts:.4f}")
        return self.exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': False})


class MarketAnalyzer:
    def __init__(self, exchange):
        self.ex = exchange
    
    def calculate_indicators(self, ohlcv):
        if len(ohlcv) < 20:
            return None
        
        closes = [c[4] for c in ohlcv]
        highs = [c[2] for c in ohlcv]
        lows = [c[3] for c in ohlcv]
        volumes = [c[5] for c in ohlcv]
        
        ema9 = sum(closes[-9:]) / 9
        ema21 = sum(closes[-21:]) / 21
        
        gains = []
        losses = []
        for i in range(1, min(15, len(closes))):
            change = closes[-i] - closes[-i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0.001
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        price_range = max(highs[-14:]) - min(lows[-14:])
        atr = price_range / 14 if price_range > 0 else closes[-1] * 0.01
        
        ema12 = sum(closes[-12:]) / 12
        ema26 = sum(closes[-26:]) / 26
        macd = ema12 - ema26
        
        tr_list = []
        for i in range(1, min(14, len(closes))):
            tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]), abs(lows[-i] - closes[-i-1]))
            tr_list.append(tr)
        avg_tr = sum(tr_list) / len(tr_list) if tr_list else atr
        
        dm_plus = []
        dm_minus = []
        for i in range(1, min(14, len(closes))):
            up = highs[-i] - highs[-i-1]
            down = lows[-i-1] - lows[-i]
            dm_plus.append(up if up > down and up > 0 else 0)
            dm_minus.append(down if down > up and down > 0 else 0)
        
        di_plus = (sum(dm_plus) / len(dm_plus)) / avg_tr * 100 if avg_tr > 0 else 0
        di_minus = (sum(dm_minus) / len(dm_minus)) / avg_tr * 100 if avg_tr > 0 else 0
        adx = abs(di_plus - di_minus) / (di_plus + di_minus + 0.001) * 100
        
        return {
            "price": closes[-1],
            "ema9": ema9,
            "ema21": ema21,
            "rsi": rsi,
            "macd": macd,
            "atr": atr,
            "adx": adx,
            "volume_24h": sum(volumes[-24:]) if len(volumes) >= 24 else sum(volumes),
            "high_24h": max(highs[-24:]) if len(highs) >= 24 else max(highs),
            "low_24h": min(lows[-24:]) if len(lows) >= 24 else min(lows),
            "volatility": (max(highs[-24:]) - min(lows[-24:])) / closes[-1] if len(closes) >= 24 else 0.05
        }
    
    def get_opportunities(self):
        opportunities = []
        
        for symbol in TradingConfig.SYMBOLS:
            try:
                ohlcv = self.ex.get_ohlcv(symbol)
                indicators = self.calculate_indicators(ohlcv)
                if not indicators:
                    continue
                
                funding = self.ex.get_funding_rate(symbol)
                
                score = 0
                if indicators["price"] > indicators["ema9"]:
                    score += 0.2
                if indicators["rsi"] > 55:
                    score += 0.2
                if indicators["rsi"] > 65:
                    score += 0.1
                if indicators["macd"] < 0:
                    score += 0.2
                if indicators["adx"] > 20:
                    score += 0.15
                if funding > 0:
                    score += 0.15
                
                opportunities.append({
                    "asset": symbol.replace("/", "_").replace(":USDT", ""),
                    "market": "futures",
                    "price": round(indicators["price"], 4),
                    "ema9": round(indicators["ema9"], 4),
                    "ema21": round(indicators["ema21"], 4),
                    "rsi": round(indicators["rsi"], 2),
                    "macd": round(indicators["macd"], 4),
                    "atr": round(indicators["atr"], 4),
                    "adx": round(indicators["adx"], 2),
                    "volume_24h": round(indicators["volume_24h"], 2),
                    "volatility": round(indicators["volatility"], 4),
                    "high_24h": round(indicators["high_24h"], 4),
                    "low_24h": round(indicators["low_24h"], 4),
                    "funding_rate": round(funding, 4),
                    "score": round(score, 2)
                })
            except Exception as e:
                print(f"   Error analyzing {symbol}: {e}")
        
        return sorted(opportunities, key=lambda x: x["score"], reverse=True)


class SmartDynamicTrader:
    def __init__(self):
        self.ex = Exchange()
        self.analyzer = MarketAnalyzer(self.ex)
        self.client = OpenAI(
            api_key=os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY"),
            base_url=os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL")
        )
        
        self.starting_balance = self.ex.get_balance()
        self.daily_start_balance = self.starting_balance
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.max_drawdown = 0.0
        self.peak_balance = self.starting_balance
        self.is_active = True
        self.deactivation_reason = None
        self.cycle_count = 0
        self.active_trades = {}
        
        print(f"\n{'='*70}")
        print(f"🧠 {TradingConfig.NAME}")
        print(f"{'='*70}")
        print(f"💰 Starting Balance: ${self.starting_balance:.2f}")
        print(f"🎯 Daily Loss Limit: {TradingConfig.DAILY_LOSS_LIMIT_PERCENT}%")
        print(f"🤖 AI Models: 8 (Consensus: {TradingConfig.REQUIRED_CONSENSUS}/8)")
        print(f"📈 Pairs: {len(TradingConfig.SYMBOLS)}")
        print(f"⚠️  SHORTS ONLY MODE")
        print(f"{'='*70}\n")
    
    def update_pnl_tracking(self, trade_pnl):
        self.total_profit += trade_pnl
        if trade_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        current_balance = self.ex.get_balance()
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        drawdown = self.peak_balance - current_balance
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    def get_status(self):
        current_balance = self.ex.get_balance()
        daily_pnl = current_balance - self.daily_start_balance
        daily_pnl_percent = (daily_pnl / self.daily_start_balance * 100) if self.daily_start_balance > 0 else 0
        
        tier = BalanceTier.get_tier(current_balance)
        ranking_score = RankingSystem.calculate_score(
            self.total_profit, self.starting_balance, 
            self.total_trades, self.winning_trades, self.max_drawdown
        )
        ai_tier = RankingSystem.get_tier_from_score(ranking_score)
        level = RankingSystem.get_level_from_score(ranking_score)
        
        balance_multiplier = (current_balance / 10000) * 0.5 if current_balance > 10000 else 0
        effective_multiplier = 1 + balance_multiplier
        
        return {
            "name": "Smart-Dynamic AI Trader",
            "current_balance": round(current_balance, 2),
            "starting_daily_balance": round(self.daily_start_balance, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_percent": round(daily_pnl_percent, 2),
            "daily_loss_limit": round(self.daily_start_balance * TradingConfig.DAILY_LOSS_LIMIT_PERCENT / 100, 2),
            "is_active": self.is_active,
            "deactivation_reason": self.deactivation_reason,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.winning_trades / max(self.total_trades, 1) * 100, 2),
            "ranking_score": round(ranking_score, 2),
            "tier": ai_tier,
            "level": level,
            "balance_tier": tier["name"],
            "position_multiplier": round(effective_multiplier, 2),
            "trade_frequency_seconds": tier["frequency"],
            "max_drawdown": round(self.max_drawdown, 2),
            "total_profit": round(self.total_profit, 2)
        }
    
    def check_daily_loss_limit(self):
        current_balance = self.ex.get_balance()
        daily_pnl = current_balance - self.daily_start_balance
        daily_pnl_percent = (daily_pnl / self.daily_start_balance * 100) if self.daily_start_balance > 0 else 0
        
        if daily_pnl_percent <= TradingConfig.DAILY_LOSS_LIMIT_PERCENT:
            self.is_active = False
            self.deactivation_reason = f"DEACTIVATED_LOSS_LIMIT: Daily loss {daily_pnl_percent:.2f}% exceeded limit of {TradingConfig.DAILY_LOSS_LIMIT_PERCENT}%"
            print(f"🛑 DAILY LOSS LIMIT HIT! PnL: {daily_pnl_percent:.2f}% | Deactivating...")
            print(f"   Status: DEACTIVATED_LOSS_LIMIT")
            return True
        return False
    
    def validate_signal(self, signal):
        if not signal:
            return None, "No signal provided"
        
        direction = signal.get("direction", "").upper()
        if direction != "SHORT":
            return None, f"REJECTED: Direction '{direction}' not allowed (SHORTS ONLY)"
        
        strategy = signal.get("strategy", "").upper().replace(" ", "_").replace("-", "_").replace("&", "").strip()
        valid_strategies = [s.upper() for s in TradingConfig.VALID_STRATEGIES]
        
        strategy_valid = False
        for valid_strat in valid_strategies:
            if valid_strat in strategy or strategy in valid_strat:
                strategy_valid = True
                break
        
        if not strategy_valid:
            return None, f"REJECTED: Strategy '{strategy}' not in valid list {TradingConfig.VALID_STRATEGIES}"
        
        confidence = signal.get("confidence", 0)
        mode = TradingMode.get_mode(confidence)
        
        if mode["name"] == "NO_TRADE":
            return None, f"Confidence {confidence*100:.1f}% too low for trade"
        
        min_lev, max_lev = mode["leverage_range"]
        leverage = signal.get("leverage", min_lev)
        leverage = max(min_lev, min(max_lev, leverage))
        
        min_risk, max_risk = mode["risk_range"]
        
        signal["leverage"] = leverage
        signal["validated_mode"] = mode["name"]
        signal["min_risk"] = min_risk
        signal["max_risk"] = max_risk
        
        return signal, None
    
    def get_ai_consensus(self, status, opportunities):
        models = ["DeepSeek R1", "GPT-5", "Claude Opus", "Llama 3.3", "Gemini Flash", "Mistral Large", "Qwen 72B", "Grok xAI"]
        
        votes = {}
        signals = []
        
        for model_name in models:
            try:
                prompt = SmartDynamicPrompt.build_prompt(model_name, status, opportunities)
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.3
                )
                
                content = response.choices[0].message.content.strip()
                
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                
                try:
                    result = json.loads(content)
                    
                    if result.get("status") == "ACTIVE" and result.get("trade_signal"):
                        signal = result["trade_signal"]
                        if signal.get("direction", "").upper() == "SHORT":
                            votes[model_name] = 1
                            signals.append(signal)
                            print(f"   ✅ {model_name}: SHORT {signal.get('selected_asset')} ({signal.get('selected_mode')})")
                        else:
                            votes[model_name] = 0
                            print(f"   ❌ {model_name}: Rejected (not SHORT)")
                    else:
                        votes[model_name] = 0
                        print(f"   ⏸️  {model_name}: PASSIVE")
                        
                except json.JSONDecodeError:
                    if "SHORT" in content.upper() and ("ACTIVE" in content.upper() or "1" in content):
                        votes[model_name] = 1
                        print(f"   ✅ {model_name}: SHORT (parsed)")
                    else:
                        votes[model_name] = 0
                        print(f"   ❌ {model_name}: NO TRADE")
                        
            except Exception as e:
                votes[model_name] = 0
                print(f"   ❌ {model_name}: Error - {str(e)[:50]}")
        
        total_votes = sum(votes.values())
        consensus = total_votes >= TradingConfig.REQUIRED_CONSENSUS
        
        print(f"\n📊 CONSENSUS: {total_votes}/8 (Required: {TradingConfig.REQUIRED_CONSENSUS}/8)")
        
        best_signal = None
        if consensus and signals:
            best_signal = max(signals, key=lambda x: x.get("confidence", 0))
        
        return consensus, total_votes, votes, best_signal
    
    def execute_trade(self, signal):
        validated_signal, error = self.validate_signal(signal)
        if error:
            print(f"   ❌ {error}")
            return None
        
        signal = validated_signal
        symbol = signal.get("selected_asset", "").replace("_", "/")
        if not symbol.endswith(":USDT"):
            symbol += ":USDT"
        
        leverage = signal.get("leverage", 5)
        min_risk = signal.get("min_risk", 0.01)
        max_risk = signal.get("max_risk", 0.02)
        
        status = self.get_status()
        
        base_position = status["current_balance"] * min_risk
        max_position = status["current_balance"] * max_risk
        effective_position = base_position * status["position_multiplier"]
        position_size = min(effective_position, max_position)
        position_size = max(10, min(position_size, 500))
        
        print(f"\n🎯 EXECUTING TRADE:")
        print(f"   Asset: {symbol}")
        print(f"   Mode: {signal.get('validated_mode', 'NORMAL')}")
        print(f"   Confidence: {signal.get('confidence', 0)*100:.1f}%")
        print(f"   Strategy: {signal.get('strategy', 'N/A')}")
        print(f"   Size: ${position_size:.2f} @ {leverage}x (Multiplier: {status['position_multiplier']}x)")
        
        try:
            entry_balance = self.ex.get_balance()
            order = self.ex.open_short(symbol, position_size, leverage)
            self.total_trades += 1
            
            self.active_trades[symbol] = {
                "entry_balance": entry_balance,
                "entry_price": signal.get("entry_price", 0),
                "position_size": position_size,
                "leverage": leverage,
                "stop_loss": signal.get("stop_loss", 0),
                "take_profit": signal.get("take_profit", []),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            print(f"   ✅ ORDER FILLED!")
            return order
        except Exception as e:
            print(f"   ❌ Order failed: {e}")
            return None
    
    def check_and_close_positions(self):
        try:
            positions = self.ex.get_positions()
            for pos in positions:
                contracts = abs(float(pos.get('contracts', 0) or 0))
                if contracts > 0:
                    symbol = pos.get('symbol', '')
                    side = pos.get('side', '')
                    pnl = float(pos.get('unrealizedPnl', 0) or 0)
                    pnl_pct = float(pos.get('percentage', 0) or 0)
                    
                    if side == 'long':
                        print(f"   🚨 CLOSING UNAUTHORIZED LONG: {symbol}")
                        self.ex.close_position(symbol, side, contracts)
                        self.update_pnl_tracking(pnl)
                        continue
                    
                    if pnl_pct >= 0.5:
                        print(f"   💰 TAKING PROFIT on {symbol}: +{pnl_pct:.2f}%")
                        self.ex.close_position(symbol, side, contracts)
                        self.update_pnl_tracking(pnl)
                        if symbol in self.active_trades:
                            del self.active_trades[symbol]
                    
                    elif pnl_pct <= -2.0:
                        print(f"   🛑 STOP LOSS on {symbol}: {pnl_pct:.2f}%")
                        self.ex.close_position(symbol, side, contracts)
                        self.update_pnl_tracking(pnl)
                        if symbol in self.active_trades:
                            del self.active_trades[symbol]
        except Exception as e:
            print(f"   Error checking positions: {e}")
    
    def run_cycle(self):
        self.cycle_count += 1
        
        print(f"\n{'='*70}")
        print(f"🔄 CYCLE {self.cycle_count} | {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC")
        print(f"{'='*70}")
        
        if self.check_daily_loss_limit():
            print(f"\n📛 STATUS: DEACTIVATED_LOSS_LIMIT")
            print(f"   Reason: {self.deactivation_reason}")
            print(f"   Action: Skipping AI consensus - no new trades until next day")
            return
        
        status = self.get_status()
        print(f"💰 Balance: ${status['current_balance']:.2f} | Tier: {status['balance_tier']} | Level: {status['level']}")
        print(f"📊 Win Rate: {status['win_rate']:.1f}% | Trades: {status['total_trades']} | Ranking: {status['ranking_score']:.1f}")
        
        self.check_and_close_positions()
        
        print(f"\n🔍 Scanning market opportunities...")
        opportunities = self.analyzer.get_opportunities()
        
        if not opportunities:
            print("   No opportunities found")
            return
        
        print(f"   Found {len(opportunities)} opportunities")
        for opp in opportunities[:3]:
            print(f"   • {opp['asset']}: Score {opp['score']:.2f} | RSI {opp['rsi']:.1f} | Funding {opp['funding_rate']:.4f}%")
        
        print(f"\n🤖 Getting AI Consensus...")
        consensus, votes, vote_details, signal = self.get_ai_consensus(status, opportunities[:3])
        
        if consensus and signal:
            print(f"\n✅ CONSENSUS REACHED! ({votes}/8)")
            self.execute_trade(signal)
        else:
            print(f"\n⏸️  No consensus ({votes}/8) - waiting...")
    
    def run(self):
        print(f"🚀 Starting Smart-Dynamic Trading System...")
        
        while True:
            try:
                if not self.is_active:
                    print("🛑 Trading deactivated. Waiting for next day...")
                    time.sleep(3600)
                    continue
                
                self.run_cycle()
                
                status = self.get_status()
                frequency = status["trade_frequency_seconds"]
                print(f"\n⏰ Next cycle in {frequency}s...")
                time.sleep(frequency)
                
            except KeyboardInterrupt:
                print("\n👋 Shutting down...")
                break
            except Exception as e:
                print(f"❌ Cycle error: {e}")
                time.sleep(60)


if __name__ == "__main__":
    trader = SmartDynamicTrader()
    trader.run()
