import numpy as np
import pandas as pd


class PerformanceAnalytics:

    def __init__(self):
        self.trades = []
        self.equity_curve = []

    def record_trade(self, pnl):
        self.trades.append(pnl)

    def record_equity(self, balance):
        self.equity_curve.append(balance)

    def stats(self):

        if not self.trades:
            return {}

        trades = np.array(self.trades)

        winrate = (trades > 0).mean()
        avg_win = trades[trades > 0].mean() if (trades > 0).any() else 0
        avg_loss = trades[trades < 0].mean() if (trades < 0).any() else 0

        equity = pd.Series(self.equity_curve)
        returns = equity.pct_change().dropna()

        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if len(returns) > 1 else 0
        drawdown = (equity.cummax() - equity).max()

        return {
            "Total Trades": len(trades),
            "Winrate": round(winrate, 3),
            "Sharpe": round(sharpe, 3),
            "Max Drawdown": round(drawdown, 2),
            "Final Balance": round(equity.iloc[-1], 2)
        }
