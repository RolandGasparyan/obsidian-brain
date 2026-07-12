import time


class Scheduler:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, interval):
        self.tasks.append({
            "func": func,
            "interval": interval,
            "last_run": 0
        })

    def run(self):
        while True:
            now = time.time()
            for task in self.tasks:
                if now - task["last_run"] >= task["interval"]:
                    task["func"]()
                    task["last_run"] = now
            time.sleep(1)
