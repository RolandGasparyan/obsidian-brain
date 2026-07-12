import numpy as np


class PerformanceTracker:
    def __init__(self, portfolio):
        self.portfolio = portfolio

    def winrate(self):
        wins = [t for t in self.portfolio.trade_history if t["pnl"] > 0]
        total = len(self.portfolio.trade_history)

        if total == 0:
            return 0

        return len(wins) / total * 100

    def max_drawdown(self):
        equity = np.array(self.portfolio.equity_curve)

        if len(equity) == 0:
            return 0

        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        return drawdown.min() * 100
import numpy as np


class PerformanceTracker:
    def __init__(self, portfolio):
        self.portfolio = portfolio

    def winrate(self):
        wins = [t for t in self.portfolio.trade_history if t["pnl"] > 0]
        total = len(self.portfolio.trade_history)

        if total == 0:
            return 0

        return len(wins) / total * 100

    def max_drawdown(self):
        equity = np.array(self.portfolio.equity_curve)

        if len(equity) == 0:
            return 0

        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        return drawdown.min() * 100
