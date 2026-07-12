"""
Quantitative Core Engine
Event-driven trading system
"""

from datetime import datetime, UTC
import time


class CoreEngine:
    def __init__(self, event_bus):
        self.bus = event_bus
        self.running = False

    def start(self):
        print("🚀 Quant Core Engine Started")
        self.running = True
        self.bus.emit("ENGINE_START")

    def stop(self):
        print("🛑 Engine Stopped")
        self.running = False
        self.bus.emit("ENGINE_STOP")

    def run_loop(self, interval=30):
        """
        Main event loop
        """
        self.start()

        while self.running:
            try:
                now = datetime.now(UTC)

                # Trigger market data event
                self.bus.emit("MARKET_TICK", {"timestamp": now})

                time.sleep(interval)

            except Exception as e:
                print(f"Engine error: {e}")
class QuantEngine:
    def __init__(self, bus, data_feed):
        self.bus = bus
        self.data_feed = data_feed
        self.running = False

    def start(self):
        print("🚀 Engine Started")
        self.running = True

    def stop(self):
        print("🛑 Engine Stopped")
        self.running = False

    def run(self):
        self.start()

        for data in self.data_feed.stream():
            if not self.running:
                break

            self.bus.emit("MARKET_DATA", data)

        self.stop()
