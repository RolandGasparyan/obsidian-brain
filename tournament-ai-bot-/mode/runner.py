from core.event_bus import EventBus
from core.engine import QuantEngine
from data.live_feed import LiveDataFeed
from data.backtest_feed import BacktestDataFeed
from execution.simulated_execution import SimulatedExecution
from risk.risk_engine import RiskManager


def run(mode="live"):

    bus = EventBus()

    if mode == "live":
        data_feed = LiveDataFeed()
    else:
        data_feed = BacktestDataFeed("data/btc_15m.csv")

    portfolio = {"cash": 100000}
    execution = SimulatedExecution(portfolio)
    risk = RiskManager(0.01)

    engine = QuantEngine(bus, data_feed)

    def on_market_data(event):
        df = event["dataframe"]
        price = event["price"]

        # Եթե դիրք չկա → open trade
        if not execution.position:

            if df["close"].iloc[-1] > df["close"].iloc[-2]:

                stop = price * 0.995
                target = price * 1.01

                size = risk.calculate_position_size(
                    portfolio["cash"],
                    price,
                    stop
                )

                execution.open_position("LONG", price, stop, target, size)

        # Եթե դիրք կա → check exit
        else:
            execution.check_exit(price)

    bus.register("MARKET_DATA", on_market_data)

    engine.run())
