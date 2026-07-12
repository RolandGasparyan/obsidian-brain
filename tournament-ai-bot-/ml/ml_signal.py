import numpy as np


class MLSignal:

    def __init__(self, model=None):
        self.model = model

    def predict(self, features):

        # Simple probability demo
        prob = np.random.random()

        if prob > 0.6:
            return "LONG"

        elif prob < 0.4:
            return "SHORT"

        return None
