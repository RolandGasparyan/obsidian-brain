import time
from data.data_feed import get_latest_data

class LiveDataFeed:
    def __init__(self, interval=30):
        self.interval = interval

    def stream(self):
        while True:
            df = get_latest_data()

            yield {
                "price": df["close"].iloc[-1],
                "dataframe": df
            }

            time.sleep(self.interval)
