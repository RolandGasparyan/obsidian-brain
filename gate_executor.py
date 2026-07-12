"""
Gate.io Executor for AI Championship
SHORT-ONLY Futures Trading
"""
import os
import ccxt
import json
from datetime import datetime

class GateExecutor:
    def __init__(self):
        self.exchange = ccxt.gateio({
            'apiKey': os.getenv('GATE_API_KEY'),
            'secret': os.getenv('GATE_API_SECRET'),
            'options': {'defaultType': 'swap'}
        })
        self.POSITION_SIZE = 200.0
        self.LEVERAGE = 50
        self.SYMBOLS = ["SOL/USDT:USDT", "XRP/USDT:USDT", "AVAX/USDT:USDT", "DOGE/USDT:USDT", "LINK/USDT:USDT"]
    
    def get_balance(self):
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get('USDT', {}).get('free', 0))
        except:
            return 0
    
    def get_price(self, symbol):
        ticker = self.exchange.fetch_ticker(symbol)
        return float(ticker['last'])
    
    def get_funding_rate(self, symbol):
        try:
            funding = self.exchange.fetch_funding_rate(symbol)
            return float(funding.get('fundingRate', 0)) * 100
        except:
            return 0
    
    def open_short(self, symbol, model_name):
        """Open SHORT position for a winning AI model"""
        try:
            self.exchange.set_leverage(self.LEVERAGE, symbol)
        except:
            pass
        
        price = self.get_price(symbol)
        size = (self.POSITION_SIZE * self.LEVERAGE) / price
        
        sl_pct = 0.02
        sl_price = round(price * (1 + sl_pct / 100), 4)
        
        print(f"   [{model_name}] Opening SHORT: {symbol} | Size: {size:.4f}")
        
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
            print(f"   [{model_name}] SL placed at ${sl_price}")
        except Exception as e:
            print(f"   [{model_name}] SL failed: {e}")
        
        return order, price, sl_price
    
    def close_position(self, symbol):
        """Close any open position - SHORTS ONLY MODE"""
        for pos in self.exchange.fetch_positions([symbol]):
            contracts = abs(float(pos.get('contracts', 0) or 0))
            if contracts > 0:
                side = pos.get('side')
                if side == 'short':
                    # Close SHORT by buying back
                    return self.exchange.create_market_buy_order(symbol, contracts, params={'reduceOnly': True})
                elif side == 'long':
                    # FORBIDDEN: Close any existing LONG immediately
                    print(f"⚠️ CLOSING FORBIDDEN LONG on {symbol}!")
                    return self.exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': True})
        return None
    
    def close_all_longs(self):
        """Close ALL long positions - SHORTS ONLY MODE ENFORCEMENT"""
        closed = 0
        for pos in self.exchange.fetch_positions():
            contracts = abs(float(pos.get('contracts', 0) or 0))
            side = pos.get('side')
            if contracts > 0 and side == 'long':
                symbol = pos['symbol']
                print(f"🚨 CLOSING FORBIDDEN LONG: {symbol}")
                self.exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': True})
                closed += 1
        return closed
    
    def get_positions(self):
        """Get all open positions"""
        positions = []
        for pos in self.exchange.fetch_positions():
            contracts = float(pos.get('contracts', 0) or 0)
            if contracts != 0:
                positions.append({
                    'symbol': pos['symbol'],
                    'side': pos['side'],
                    'size': abs(contracts),
                    'entry': float(pos['entryPrice']),
                    'pnl': float(pos.get('unrealizedPnl', 0))
                })
        return positions
    
    def get_market_data(self, symbol):
        """Get market data for AI analysis"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, '1m', limit=50)
            closes = [c[4] for c in ohlcv]
            highs = [c[2] for c in ohlcv]
            lows = [c[3] for c in ohlcv]
            volumes = [c[5] for c in ohlcv]
            
            price = closes[-1]
            ema9 = sum(closes[-9:]) / 9
            
            changes = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
            atr = sum(changes[-14:]) / 14 if len(changes) >= 14 else sum(changes) / len(changes)
            
            gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
            losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
            avg_gain = sum(gains[-14:]) / 14
            avg_loss = sum(losses[-14:]) / 14
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            ema12 = sum(closes[-12:]) / 12
            ema26 = sum(closes[-26:]) / 26
            macd = ema12 - ema26
            
            tr_list = []
            for i in range(1, len(closes)):
                tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
                tr_list.append(tr)
            atr14 = sum(tr_list[-14:]) / 14 if len(tr_list) >= 14 else sum(tr_list) / len(tr_list)
            
            dm_plus = []
            dm_minus = []
            for i in range(1, len(closes)):
                up = highs[i] - highs[i-1]
                down = lows[i-1] - lows[i]
                dm_plus.append(up if up > down and up > 0 else 0)
                dm_minus.append(down if down > up and down > 0 else 0)
            
            di_plus = (sum(dm_plus[-14:]) / atr14) * 100 if atr14 > 0 else 0
            di_minus = (sum(dm_minus[-14:]) / atr14) * 100 if atr14 > 0 else 0
            dx = abs(di_plus - di_minus) / (di_plus + di_minus) * 100 if (di_plus + di_minus) > 0 else 0
            adx = dx
            
            volume = sum(volumes[-5:]) / 5 * price / 1e9
            
            funding = self.get_funding_rate(symbol)
            
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
            print(f"Error getting market data for {symbol}: {e}")
            return None


if __name__ == "__main__":
    executor = GateExecutor()
    print(f"Balance: ${executor.get_balance():.2f}")
    print(f"Positions: {executor.get_positions()}")
