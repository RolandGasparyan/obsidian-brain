class PortfolioEngine:

    def __init__(self, initial_capital=100000):
        self.cash = initial_capital
        self.positions = {}

    def update_cash(self, pnl):
        self.cash += pnl

    def open_position(self, symbol, position_data):
        self.positions[symbol] = position_data

    def close_position(self, symbol):
        if symbol in self.positions:
            del self.positions[symbol]

    def get_balance(self):
        return self.cash
