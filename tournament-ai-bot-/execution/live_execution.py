import ccxt


class LiveExecution:

    def __init__(self, api_key, secret):
        self.exchange = ccxt.gateio({
            "apiKey": api_key,
            "secret": secret
        })

    def market_buy(self, symbol, amount):
        return self.exchange.create_market_buy_order(symbol, amount)

    def market_sell(self, symbol, amount):
        return self.exchange.create_market_sell_order(symbol, amount)
