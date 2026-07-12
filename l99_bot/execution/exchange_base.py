"""
L99 Execution — Exchange Base
Abstract interface all exchange adapters must implement.
Strategy engine interacts ONLY through this contract.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class HealthStatus:
    exchange_id:    str
    healthy:        bool
    latency_ms:     float
    reason:         str = ""


class ExchangeBase(ABC):
    exchange_id: str = "UNKNOWN"

    @abstractmethod
    def get_balance(self) -> dict:
        """Returns {'USDT': {'free': float, 'used': float, 'total': float}}"""

    @abstractmethod
    def get_orderbook(self, symbol: str) -> dict:
        """Returns {'bid': float, 'ask': float, 'timestamp': float}"""

    @abstractmethod
    def place_order(self, symbol: str, side: str, size: float,
                    order_type: str, price: float | None = None,
                    params: dict | None = None) -> dict:
        """Returns {'id': str, 'status': str, 'price': float, ...}"""

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> None:
        """Cancels order — swallows exchange errors, logs warning."""

    @abstractmethod
    def fetch_order(self, order_id: str, symbol: str) -> dict:
        """Returns {'id': str, 'status': str, 'filled': float, ...}"""

    @abstractmethod
    def fetch_open_positions(self) -> list[dict]:
        """Returns list of open position dicts."""

    @abstractmethod
    def fetch_recent_trades(self, symbol: str, limit: int = 10) -> list[dict]:
        """Returns recent closed trades for slippage analysis."""

    @abstractmethod
    def create_market_order(self, symbol: str, side: str, size: float) -> dict:
        """Market order for emergency flatten."""

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """Lightweight liveness probe — must return in < 2s."""
