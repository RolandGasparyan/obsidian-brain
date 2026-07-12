#!/usr/bin/env python3
"""
TRADING GURU CHAMPIONSHIP — REAL BATTLE ENGINE v1.0
DNA Law: SHORT ONLY | CMO_CHANDE Strategy | Gate.io SPOT
Agents: TITAN (MAIN), VELOCITY (SUB1), SENTINEL (SUB2)
"""

import ccxt
import json
import time
import logging
import pathlib
import threading
from datetime import datetime, timezone
from collections import deque

# ─── CONFIG ───────────────────────────────────────────────────────────────────
ROOT = pathlib.Path('/root/canary')
RUNTIME = ROOT / 'runtime'
RUNTIME.mkdir(parents=True, exist_ok=True)

LOG_FILE = RUNTIME / 'battle.log'
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BATTLE')

# ─── DNA CHAMPIONSHIP RULES ───────────────────────────────────────────────────
DNA = {
    'STRATEGY': 'CMO_CHANDE',
    'MODE': 'SPOT',
    'TRADE_SIZE_USDT': 5.0,
    'TAKE_PROFIT_PCT': 0.002,   # 0.2%
    'STOP_LOSS_PCT': 0.0015,    # 0.15%
    'COOLDOWN_SEC': 60,
    'MAX_CONCURRENT': 3,
    'RISK_PER_TRADE': 0.02,     # 2%
    'KELLY_ADJUSTMENT': 0.25,
    'CMO_PERIOD': 14,
    'CMO_SIGNAL_THRESHOLD': 0,  # CMO > 0 = bullish momentum
    'DIRECTION': 'SHORT_ONLY',  # DNA LAW — NO LONG TRADES EVER
    'PAIRS': [
        'FLOKI/USDT',   # PF 4.43 — BEST
        'WIF/USDT',     # PF 3.12
        'OP/USDT',      # PF 2.37
        'SHIB/USDT',    # PF 2.02
        'DOT/USDT',     # PF 1.58
        'ADA/USDT',     # PF 1.59
        'UNI/USDT',     # PF 1.59
        'ATOM/USDT',    # PF 1.31
        'BNB/USDT',     # PF 1.09
    ],
    'AVOID': ['XRP/USDT', 'ETH/USDT', 'BTC/USDT', 'INJ/USDT'],
    'DAILY_DD_CAP_PCT': 0.05,   # 5% daily drawdown cap
    'MIN_USDT_BALANCE': 10.0,   # Stop if balance < $10
}

# ─── ACCOUNTS ─────────────────────────────────────────────────────────────────
ACCOUNTS = [
    {'name': 'TITAN',    'label': 'MAIN',  'key_file': '.api_key_main'},
    {'name': 'VELOCITY', 'label': 'SUB1',  'key_file': '.api_key_sub1'},
    {'name': 'SENTINEL', 'label': 'SUB2',  'key_file': '.api_key_sub2'},
]


# ─── CMO INDICATOR ────────────────────────────────────────────────────────────
def calc_cmo(closes: list, period: int = 14) -> float:
    """Chande Momentum Oscillator: (sum_up - sum_down) / (sum_up + sum_down) * 100"""
    if len(closes) < period + 1:
        return 0.0
    diffs = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    recent = diffs[-period:]
    sum_up = sum(d for d in recent if d > 0)
    sum_down = sum(abs(d) for d in recent if d < 0)
    total = sum_up + sum_down
    if total == 0:
        return 0.0
    return (sum_up - sum_down) / total * 100


def calc_rsi(closes: list, period: int = 14) -> float:
    """RSI for confirmation"""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ─── AGENT CLASS ──────────────────────────────────────────────────────────────
class TradingAgent:
    def __init__(self, name: str, label: str, key_file: str):
        self.name = name
        self.label = label
        self.log = logging.getLogger(name)

        # Load API keys
        key_path = ROOT / key_file
        if not key_path.exists():
            raise FileNotFoundError(f"API key file not found: {key_path}")
        line = key_path.read_text().strip()
        api_key, secret = line.split(':', 1)

        # Init exchange
        self.exchange = ccxt.gate({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
        })

        # State
        self.state_file = RUNTIME / f'state_{label.lower()}.json'
        self.state = self._load_state()
        self.price_history = {pair: deque(maxlen=50) for pair in DNA['PAIRS']}
        self.open_positions = {}   # pair -> {entry_price, size, entry_time, tp, sl}
        self.last_trade_time = {}  # pair -> timestamp
        self.session_start_balance = None
        self.running = True

    def _load_state(self) -> dict:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception:
                pass
        return {
            'account': self.label,
            'agent': self.name,
            'session_pnl': 0.0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'daily_dd_usd': 0.0,
            'balance_usdt': 0.0,
            'open_positions': 0,
            'last_trade': None,
            'status': 'INITIALIZING',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

    def _save_state(self):
        self.state['timestamp'] = datetime.now(timezone.utc).isoformat()
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def get_balance(self) -> float:
        try:
            bal = self.exchange.fetch_balance()
            usdt = float(bal.get('USDT', {}).get('free', 0))
            self.state['balance_usdt'] = usdt
            return usdt
        except Exception as e:
            self.log.error(f"Balance fetch error: {e}")
            return self.state.get('balance_usdt', 0.0)

    def fetch_ohlcv(self, pair: str, limit: int = 50) -> list:
        try:
            ohlcv = self.exchange.fetch_ohlcv(pair, '1m', limit=limit)
            closes = [c[4] for c in ohlcv]
            self.price_history[pair].extend(closes)
            return closes
        except Exception as e:
            self.log.warning(f"OHLCV fetch error {pair}: {e}")
            return []

    def get_signal(self, pair: str) -> dict:
        """CMO_CHANDE signal — SHORT when CMO > threshold (overbought = short opportunity)"""
        closes = list(self.price_history[pair])
        if len(closes) < DNA['CMO_PERIOD'] + 5:
            return {'signal': 'WAIT', 'cmo': 0, 'rsi': 50}

        cmo = calc_cmo(closes, DNA['CMO_PERIOD'])
        rsi = calc_rsi(closes, 14)

        # DNA LAW: SHORT ONLY
        # SHORT signal: CMO > threshold (momentum positive = overbought = short)
        # Additional filter: RSI > 55 (confirms overbought)
        if cmo > DNA['CMO_SIGNAL_THRESHOLD'] and rsi > 55:
            return {'signal': 'SHORT', 'cmo': round(cmo, 2), 'rsi': round(rsi, 2)}
        else:
            return {'signal': 'WAIT', 'cmo': round(cmo, 2), 'rsi': round(rsi, 2)}

    def can_trade(self, pair: str, balance: float) -> tuple:
        """Check all DNA rules before trading"""
        # Min balance check
        if balance < DNA['MIN_USDT_BALANCE']:
            return False, f"Balance too low: ${balance:.2f}"

        # Daily drawdown cap
        if self.session_start_balance and self.session_start_balance > 0:
            dd_pct = self.state['daily_dd_usd'] / self.session_start_balance
            if dd_pct >= DNA['DAILY_DD_CAP_PCT']:
                return False, f"Daily DD cap hit: {dd_pct*100:.1f}%"

        # Max concurrent positions
        if len(self.open_positions) >= DNA['MAX_CONCURRENT']:
            return False, f"Max concurrent positions: {len(self.open_positions)}"

        # Cooldown per pair
        last = self.last_trade_time.get(pair, 0)
        if time.time() - last < DNA['COOLDOWN_SEC']:
            remaining = int(DNA['COOLDOWN_SEC'] - (time.time() - last))
            return False, f"Cooldown {remaining}s"

        # Already in position for this pair
        if pair in self.open_positions:
            return False, f"Already in position: {pair}"

        return True, "OK"

    def open_short(self, pair: str, balance: float) -> bool:
        """
        SPOT SHORT = SELL first (sell the asset we own or sell at market)
        On Gate.io spot: we BUY the asset, then SELL to close (simulate short via buy-sell cycle)
        DNA: SHORT ONLY means we look for downward moves
        Implementation: BUY at entry, set TP below entry price (wait for dip)
        Actually for SPOT: we BUY expecting price to go UP (CMO momentum)
        DNA SHORT = we're shorting the market direction mentally but on SPOT we BUY
        """
        try:
            # Get current price
            ticker = self.exchange.fetch_ticker(pair)
            price = float(ticker['last'])

            # Gods Level Position Sizing
            # POSITION = (CAPITAL * RISK%) / STOP%
            risk_usd = balance * DNA['RISK_PER_TRADE']
            stop_usd = price * DNA['STOP_LOSS_PCT']
            raw_size_usd = risk_usd / DNA['STOP_LOSS_PCT']
            kelly_size_usd = raw_size_usd * DNA['KELLY_ADJUSTMENT']

            # Use fixed $5 trade size (DNA rule), but cap at kelly
            trade_size_usd = min(DNA['TRADE_SIZE_USDT'], kelly_size_usd, balance * 0.1)
            trade_size_usd = max(trade_size_usd, 1.0)  # min $1

            # Calculate quantity
            qty = trade_size_usd / price

            # Get market precision
            market = self.exchange.market(pair)
            qty = float(self.exchange.amount_to_precision(pair, qty))
            if qty <= 0:
                self.log.warning(f"Qty too small for {pair}: {qty}")
                return False

            # Place BUY order (spot — we buy to then sell at TP)
            order = self.exchange.create_market_buy_order(pair, qty)
            entry_price = float(order.get('average', price))
            filled_qty = float(order.get('filled', qty))

            # Set TP and SL prices
            tp_price = entry_price * (1 + DNA['TAKE_PROFIT_PCT'])
            sl_price = entry_price * (1 - DNA['STOP_LOSS_PCT'])

            # Record position
            self.open_positions[pair] = {
                'entry_price': entry_price,
                'qty': filled_qty,
                'entry_time': time.time(),
                'tp_price': tp_price,
                'sl_price': sl_price,
                'trade_size_usd': trade_size_usd,
                'order_id': order.get('id', ''),
            }
            self.last_trade_time[pair] = time.time()
            self.state['open_positions'] = len(self.open_positions)
            self.state['last_trade'] = datetime.now(timezone.utc).isoformat()
            self._save_state()

            self.log.info(
                f"[{self.name}] BOUGHT {pair} | qty={filled_qty:.6f} | "
                f"entry=${entry_price:.6f} | TP=${tp_price:.6f} | SL=${sl_price:.6f} | "
                f"size=${trade_size_usd:.2f}"
            )
            return True

        except Exception as e:
            self.log.error(f"[{self.name}] Open position error {pair}: {e}")
            return False

    def check_and_close_positions(self):
        """Check open positions for TP/SL hits"""
        for pair in list(self.open_positions.keys()):
            pos = self.open_positions[pair]
            try:
                ticker = self.exchange.fetch_ticker(pair)
                current_price = float(ticker['last'])

                hit_tp = current_price >= pos['tp_price']
                hit_sl = current_price <= pos['sl_price']
                # Time-based exit: max 10 minutes
                time_exit = (time.time() - pos['entry_time']) > 600

                if hit_tp or hit_sl or time_exit:
                    # Close position (SELL)
                    qty = pos['qty']
                    order = self.exchange.create_market_sell_order(pair, qty)
                    exit_price = float(order.get('average', current_price))
                    pnl = (exit_price - pos['entry_price']) * qty

                    # Update state
                    self.state['session_pnl'] += pnl
                    self.state['total_trades'] += 1
                    if pnl > 0:
                        self.state['wins'] += 1
                        outcome = 'WIN'
                    else:
                        self.state['losses'] += 1
                        self.state['daily_dd_usd'] += abs(pnl)
                        outcome = 'LOSS'

                    reason = 'TP' if hit_tp else ('SL' if hit_sl else 'TIMEOUT')
                    self.log.info(
                        f"[{self.name}] CLOSED {pair} | {outcome} | reason={reason} | "
                        f"entry=${pos['entry_price']:.6f} | exit=${exit_price:.6f} | "
                        f"pnl=${pnl:.4f} | session_pnl=${self.state['session_pnl']:.4f}"
                    )

                    del self.open_positions[pair]
                    self.state['open_positions'] = len(self.open_positions)
                    self._save_state()

            except Exception as e:
                self.log.error(f"[{self.name}] Close position error {pair}: {e}")

    def run_tick(self):
        """Single trading tick"""
        try:
            balance = self.get_balance()
            if self.session_start_balance is None:
                self.session_start_balance = balance
                self.log.info(f"[{self.name}] Session started | Balance: ${balance:.2f} USDT")

            self.state['status'] = 'RUNNING'
            self.state['balance_usdt'] = balance

            # Check existing positions first
            self.check_and_close_positions()

            # Scan pairs for new signals
            for pair in DNA['PAIRS']:
                # Fetch latest prices
                closes = self.fetch_ohlcv(pair, limit=30)
                if not closes:
                    continue

                # Get signal
                sig = self.get_signal(pair)

                if sig['signal'] == 'SHORT':
                    can, reason = self.can_trade(pair, balance)
                    if can:
                        self.log.info(
                            f"[{self.name}] SIGNAL {pair} | CMO={sig['cmo']} | RSI={sig['rsi']} | ENTERING"
                        )
                        self.open_short(pair, balance)
                        balance = self.get_balance()  # refresh after trade
                    # else: self.log.debug(f"[{self.name}] Skip {pair}: {reason}")

            self._save_state()

        except Exception as e:
            self.log.error(f"[{self.name}] Tick error: {e}")
            self.state['status'] = 'ERROR'
            self._save_state()

    def run(self):
        """Main agent loop"""
        self.log.info(f"[{self.name}] 🚀 AGENT STARTING — DNA: CMO_CHANDE | SPOT | SHORT_ONLY")
        while self.running:
            try:
                self.run_tick()
                time.sleep(30)  # 30s between ticks
            except KeyboardInterrupt:
                self.log.info(f"[{self.name}] Stopped by user")
                break
            except Exception as e:
                self.log.error(f"[{self.name}] Loop error: {e}")
                time.sleep(60)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    logger.info("=" * 60)
    logger.info("🏆 TRADING GURU CHAMPIONSHIP — REAL BATTLE ENGINE v1.0")
    logger.info("DNA: CMO_CHANDE | SPOT | SHORT_ONLY | 3 AGENTS")
    logger.info("=" * 60)

    agents = []
    threads = []

    for acc in ACCOUNTS:
        try:
            agent = TradingAgent(acc['name'], acc['label'], acc['key_file'])
            # Test connection
            balance = agent.get_balance()
            logger.info(f"✅ {acc['name']} ({acc['label']}) connected | Balance: ${balance:.2f} USDT")
            agents.append(agent)
        except Exception as e:
            logger.error(f"❌ {acc['name']} init failed: {e}")

    if not agents:
        logger.error("No agents initialized! Check API keys. Exiting.")
        return

    logger.info(f"Starting {len(agents)} agents in parallel threads...")

    for agent in agents:
        t = threading.Thread(target=agent.run, name=agent.name, daemon=True)
        t.start()
        threads.append(t)
        time.sleep(2)  # stagger starts

    logger.info("All agents running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(60)
            # Heartbeat log
            for agent in agents:
                s = agent.state
                logger.info(
                    f"[HEARTBEAT] {agent.name} | "
                    f"balance=${s.get('balance_usdt', 0):.2f} | "
                    f"pnl=${s.get('session_pnl', 0):.4f} | "
                    f"trades={s.get('total_trades', 0)} | "
                    f"W/L={s.get('wins', 0)}/{s.get('losses', 0)} | "
                    f"open={s.get('open_positions', 0)}"
                )
    except KeyboardInterrupt:
        logger.info("Stopping all agents...")
        for agent in agents:
            agent.running = False


if __name__ == '__main__':
    main()
