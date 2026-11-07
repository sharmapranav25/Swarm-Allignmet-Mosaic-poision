class Ledger:
    def __init__(self):
        self.events = []
        self.tick = 0
    def record(self, event, **kwargs):
        self.events.append(dict(event=event, **kwargs))
