class RiskManager:
    def __init__(self, risk_per_trade=0.01):
        """
        risk_per_trade = 1% default
        """
        self.risk_per_trade = risk_per_trade

    def calculate_position_size(self, balance, entry_price, stop_loss_price):
        risk_amount = balance * self.risk_per_trade
        stop_distance = abs(entry_price - stop_loss_price)

        if stop_distance == 0:
            return 0

        position_size = risk_amount / stop_distance
        return position_size
