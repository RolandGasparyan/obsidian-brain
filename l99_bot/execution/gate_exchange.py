"""
L99 Execution — Gate.io Adapter
Secondary exchange (30% capital allocation).
Requires GATE_API_KEY + GATE_API_SECRET in .env.
"""
import logging
import time

import ccxt

import config
from execution.exchange_base import ExchangeBase, HealthStatus

logger = logging.getLogger("l99.execution.gate")


class GateExchange(ExchangeBase):
    exchange_id = "GATE"

    def __init__(self) -> None:
        self._ex = ccxt.gateio({
            "apiKey":          getattr(config, "GATE_API_KEY",    ""),
            "secret":          getattr(config, "GATE_API_SECRET", ""),
            "enableRateLimit": True,
            "options":         {"defaultType": "spot"},
        })

    def get_balance(self) -> dict:
        bal = self._ex.fetch_balance()
        usdt = bal.get("USDT", {"free": 0.0, "used": 0.0, "total": 0.0})
        return {"USDT": {"free": float(usdt["free"]),
                         "used": float(usdt["used"]),
                         "total": float(usdt["free"]) + float(usdt["used"])}}

    def get_orderbook(self, symbol: str) -> dict:
        t = self._ex.fetch_ticker(symbol)
        return {"bid": t["bid"], "ask": t["ask"], "timestamp": t["timestamp"]}

    def place_order(self, symbol: str, side: str, size: float,
                    order_type: str, price: float | None = None,
                    params: dict | None = None) -> dict:
        return self._ex.create_order(symbol, order_type, side, size, price, params or {})

    def cancel_order(self, order_id: str, symbol: str) -> None:
        try:
            self._ex.cancel_order(order_id, symbol)
        except Exception as e:
            logger.warning("Gate cancel_order failed %s: %s", order_id, e)

    def fetch_order(self, order_id: str, symbol: str) -> dict:
        return self._ex.fetch_order(order_id, symbol)

    def fetch_open_positions(self) -> list[dict]:
        orders = self._ex.fetch_open_orders()
        return [{"order_id": o["id"], "symbol": o["symbol"], "side": o["side"],
                 "size": o["amount"], "price": o["price"]} for o in orders]

    def fetch_recent_trades(self, symbol: str, limit: int = 10) -> list[dict]:
        trades = self._ex.fetch_my_trades(symbol, limit=limit)
        return [{"id": t["id"], "price": t["price"], "amount": t["amount"],
                 "timestamp": t["timestamp"]} for t in trades]

    def create_market_order(self, symbol: str, side: str, size: float) -> dict:
        return self._ex.create_market_order(symbol, side, size)

    def health_check(self) -> HealthStatus:
        t0 = time.monotonic()
        try:
            self._ex.fetch_time()
            latency_ms = (time.monotonic() - t0) * 1000
            return HealthStatus(exchange_id=self.exchange_id,
                                healthy=True, latency_ms=latency_ms)
        except Exception as e:
            latency_ms = (time.monotonic() - t0) * 1000
            return HealthStatus(exchange_id=self.exchange_id,
                                healthy=False, latency_ms=latency_ms, reason=str(e))
