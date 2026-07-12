import pandas as pd

class BacktestDataFeed:
    def __init__(self, csv_path):
        self.df = pd.read_csv(csv_path)

    def stream(self):
        for i in range(50, len(self.df)):
            window = self.df.iloc[:i]

            yield {
                "price": window["close"].iloc[-1],
                "dataframe": window
            }
