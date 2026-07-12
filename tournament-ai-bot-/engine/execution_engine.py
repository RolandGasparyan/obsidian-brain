class ExecutionEngine:
    def __init__(self):
        self.position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.size = 0

    def open_position(self, side, price, stop_loss, take_profit, size):
        self.position = side
        self.entry_price = price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.size = size

        print(f"\n🟢 OPEN {side}")
        print(f"Entry: {price}")
        print(f"Size: {size:.4f}")
        print(f"SL: {stop_loss}")
        print(f"TP: {take_profit}")

    def close_position(self, price, reason):
        if self.position is None:
            return 0

        if self.position == "LONG":
            pnl = (price - self.entry_price) * self.size
        else:
            pnl = (self.entry_price - price) * self.size

        print(f"\n🔴 CLOSE {self.position} ({reason})")
        print(f"Exit: {price}")
        print(f"PNL: {pnl:.2f}")

        self.position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.size = 0

        return pnl
class ExecutionEngine:
    def __init__(self):
        self.position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.size = 0

    def open_position(self, side, price, stop_loss, take_profit, size):
        self.position = side
        self.entry_price = price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.size = size

        print(f"\n🟢 OPEN {side}")
        print(f"Entry: {price}")
        print(f"Size: {size:.4f}")
        print(f"SL: {stop_loss}")
        print(f"TP: {take_profit}")

    def close_position(self, price, reason):
        if self.position is None:
            return 0

        if self.position == "LONG":
            pnl = (price - self.entry_price) * self.size
        else:
            pnl = (self.entry_price - price) * self.size

        print(f"\n🔴 CLOSE {self.position} ({reason})")
        print(f"Exit: {price}")
        print(f"PNL: {pnl:.2f}")

        self.position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.size = 0

        return pnl
