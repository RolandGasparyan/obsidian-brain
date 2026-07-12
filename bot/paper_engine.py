import json
import os
from dataclasses import dataclass, asdict, field
from typing import Optional

STATE_DIR = "runtime/paper_states"
os.makedirs(STATE_DIR, exist_ok=True)

@dataclass
class Position:
    entry_price: float
    qty: float
    side: str = "long"

@dataclass
class PaperState:
    sid: str
    cash: float
    initial_balance: float
    fee_rate: float
    position: Optional[Position] = None
    trades: list = field(default_factory=list)

def load_state(sid, initial_balance=1000.0, fee_rate=0.0014):
    path = f"{STATE_DIR}/{sid}.json"
    if os.path.exists(path):
        with open(path) as f:
            d = json.load(f)
        pos = Position(**d["position"]) if d.get("position") else None
        return PaperState(
            sid=d["sid"], cash=d["cash"],
            initial_balance=d["initial_balance"],
            fee_rate=d["fee_rate"], position=pos,
            trades=d.get("trades", [])
        )
    return PaperState(sid=sid, cash=initial_balance,
                      initial_balance=initial_balance, fee_rate=fee_rate)

def save_state(ps):
    path = f"{STATE_DIR}/{ps.sid}.json"
    d = asdict(ps)
    with open(path, "w") as f:
        json.dump(d, f, indent=2)

def equity(ps, last_price):
    if ps.position:
        return ps.cash + ps.position.qty * last_price
    return ps.cash

def is_started(ps):
    return len(ps.trades) > 0 or ps.position is not None

def advance(ps, df):
    for ts, row in df.iterrows():
        sig = row.get("signal", 0)
        price = float(row["close"])
        fee = ps.fee_rate
        if sig == 1 and ps.position is None and ps.cash > 10:
            qty = (ps.cash * (1 - fee)) / price
            ps.cash = 0.0
            ps.position = Position(entry_price=price, qty=qty)
        elif sig == -1 and ps.position is not None:
            proceeds = ps.position.qty * price * (1 - fee)
            pnl = proceeds - (ps.position.qty * ps.position.entry_price)
            ps.trades.append({"ts": str(ts), "pnl": round(pnl, 4), "price": price})
            ps.cash = proceeds
            ps.position = None
    return ps
