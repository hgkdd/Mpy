class LogFreq:
    def __init__(self, start=80e6, stop=1e9, step=1.01, endpoint=True):
        self.start = start
        self.stop = stop
        self.step = step
        self.endpoint = endpoint
        self.logspace = self.logspace_gen(self.start, self.stop, self.step, self.endpoint)

    def logspace_gen(self, start, stop, step, endpoint=True):
        f = start
        while f <= stop:
            yield f
            f *= step
        if endpoint and f > stop:
            yield stop
