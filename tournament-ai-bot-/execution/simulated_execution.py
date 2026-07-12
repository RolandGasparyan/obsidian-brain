class SimulatedExecution:

    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.position = None

    def open_position(self, side, entry, stop, target, size):
        self.position = {
            "side": side,
            "entry": entry,
            "stop": stop,
            "target": target,
            "size": size
        }

        print("\n🟢 OPEN", side)
        print("Entry:", entry)
        print("Stop:", stop)
        print("Target:", target)
        print("Size:", size)

    def check_exit(self, price):
        if not self.position:
            return None

        side = self.position["side"]
        entry = self.position["entry"]
        stop = self.position["stop"]
        target = self.position["target"]
        size = self.position["size"]

        if side == "LONG":

            if price <= stop:
                pnl = (price - entry) * size
                reason = "STOP LOSS"

            elif price >= target:
                pnl = (price - entry) * size
                reason = "TAKE PROFIT"

            else:
                return None

        self.portfolio["cash"] += pnl
        print("\n🔴 CLOSE", reason)
        print("PnL:", pnl)
        print("Balance:", self.portfolio["cash"])

        self.position = None

        return pnl
