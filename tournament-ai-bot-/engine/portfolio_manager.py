class PortfolioManager:
    def __init__(self, starting_balance):
        self.balance = starting_balance
        self.equity_curve = []
        self.trade_history = []

    def update_balance(self, pnl):
        self.balance += pnl

    def record_trade(self, trade):
        self.trade_history.append(trade)

    def record_equity(self):
        self.equity_curve.append(self.balance)
class PortfolioManager:
    def __init__(self, starting_balance):
        self.balance = starting_balance
        self.equity_curve = []
        self.trade_history = []

    def update_balance(self, pnl):
        self.balance += pnl

    def record_trade(self, trade):
        self.trade_history.append(trade)

    def record_equity(self)
        self.equity_curve.append(self.balance)
