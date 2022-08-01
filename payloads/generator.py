class Registry:
    generators = {}

    @classmethod
    def register(cls, name, generator):
        if isinstance(generator, Generator):
            cls.generators[name] = generator
        else:
            raise TypeError(f"{type(generator)} is not compatible")

    @classmethod
    def get(cls, name):
        return cls.generators[name]


class Generator:

    def __init__(self, initial, end, step):
        self.initial = initial
        self.count = initial
        self.step = step
        self.end = end

    def next(self):
        payload = self.generate()
        self.count += self.step
        return payload

    def reset(self):
        self.count = self.initial

    def done(self):
        return self.count > self.end

    def generate(self):
        return self.count


class Numbers(Generator):
    pass
