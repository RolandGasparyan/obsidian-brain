class RiskManager:

    def __init__(self, risk_per_trade=0.01):
        self.risk_per_trade = risk_per_trade

    def calculate_position_size(self, capital, entry, stop):
        risk_amount = capital * self.risk_per_trade
        stop_distance = abs(entry - stop)

        if stop_distance == 0:
            return 0

        return risk_amount / stop_distance
