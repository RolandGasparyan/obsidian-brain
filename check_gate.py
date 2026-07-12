import ccxt
import os
from datetime import datetime

exchange = ccxt.gateio({
    'apiKey': os.getenv('GATE_API_KEY'),
    'secret': os.getenv('GATE_API_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'swap', 'defaultSettle': 'usdt'}
})

print('═══════════════════════════════════════════════════════════════')
print('💰 FULL GATE.IO ACCOUNT CHECK')
print('═══════════════════════════════════════════════════════════════')

# Check balance first
balance = exchange.fetch_balance()
usdt = balance.get('USDT', {})
total = float(usdt.get('total', 0) or 0)
free = float(usdt.get('free', 0) or 0)
used = float(usdt.get('used', 0) or 0)

print(f'\n💵 BALANCE:')
print(f'   Total: ${total:.2f} USDT')
print(f'   Available: ${free:.2f} USDT')
print(f'   In Use: ${used:.2f} USDT')

# Check positions
print('\n📊 OPEN POSITIONS:')
positions = exchange.fetch_positions()
open_count = 0
for pos in positions:
    contracts = abs(float(pos.get('contracts', 0) or 0))
    if contracts > 0:
        open_count += 1
        symbol = pos.get('symbol', '')
        side = pos.get('side', '')
        pnl = float(pos.get('unrealizedPnl', 0) or 0)
        print(f'   {symbol} | {side.upper()} | Size: {contracts} | PnL: ${pnl:.2f}')
        # Close it
        try:
            if side == 'short':
                exchange.create_market_buy_order(symbol, contracts, params={'reduceOnly': True})
            else:
                exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': True})
            print(f'   ✅ CLOSED!')
        except Exception as e:
            print(f'   ❌ Error closing: {e}')

if open_count == 0:
    print('   ✅ No open positions')

# Check recent trades  
print('\n📜 RECENT TRADES:')
try:
    for sym in ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'DOGE/USDT:USDT', 'XRP/USDT:USDT', 'LINK/USDT:USDT']:
        trades = exchange.fetch_my_trades(sym, limit=3)
        for t in trades:
            side = t.get('side', '').upper()
            amount = t.get('amount', 0)
            price = t.get('price', 0)
            ts = t.get('timestamp', 0)
            dt = datetime.fromtimestamp(ts/1000).strftime('%m/%d %H:%M:%S') if ts else 'N/A'
            print(f'   {dt} | {sym.split("/")[0]} | {side} | {amount} @ ${price:.4f}')
except Exception as e:
    print(f'   Error: {e}')

print('\n═══════════════════════════════════════════════════════════════')
print('⚠️  OUR BOT IS STOPPED')
print('═══════════════════════════════════════════════════════════════')
print('If you see new trades, check:')
print('1. Gate.io built-in trading bot (Strategy Trading section)')
print('2. Another computer/server running a bot')
print('3. Manual trades')
print('═══════════════════════════════════════════════════════════════')
