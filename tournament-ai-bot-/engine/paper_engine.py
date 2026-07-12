class PaperTradingEngine:
    def __init__(self, starting_balance=10000):
        self.balance = starting_balance
        self.position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.position_size = 0
        self.trade_history = []

    def open_long(self, price, stop_loss, take_profit, size):
        if self.position is None:
            self.position = "LONG"
            self.entry_price = price
            self.stop_loss = stop_loss
            self.take_profit = take_profit
            self.position_size = size

            print(f"🟢 OPEN LONG")
            print(f"Entry: {price}")
            print(f"Size: {size:.4f}")
            print(f"SL: {stop_loss}")
            print(f"TP: {take_profit}")
            print("-" * 50)

    def close_position(self, price, reason="MANUAL"):
        if self.position == "LONG":
            pnl = (price - self.entry_price) * self.position_size
            self.balance += pnl

            print(f"🔴 CLOSE LONG ({reason})")
            print(f"Exit: {price}")
            print(f"PNL: {pnl:.2f}")
            print(f"New Balance: {self.balance:.2f}")
            print("=" * 50)

            self.trade_history.append({
                "entry": self.entry_price,
                "exit": price,
                "size": self.position_size,
                "pnl": pnl,
                "reason": reason
            })

            self.position = None
            self.entry_price = None
            self.stop_loss = None
            self.take_profit = None
            self.position_size = 0

    def check_exit_conditions(self, current_price):
        if self.position == "LONG":
            if current_price <= self.stop_loss:
                self.close_position(current_price, reason="STOP LOSS")

            elif current_price >= self.take_profit:
                self.close_position(current_price, reason="TAKE PROFIT")
