class Generator:

    def __init__(self, initial, end):
        self.count = initial
        self.end = end

    def next(self):
        payload = self.generate()
        self.count += 1
        return payload

    def done(self):
        return self.count > self.end

    def generate(self):
        return self.count