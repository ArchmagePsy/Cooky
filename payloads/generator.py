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

    def __init__(self, name, initial, end, step):
        self.name = name
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

    @classmethod
    def setup(cls):
        name = input("Choose a name for this payload: ")
        initial = int(input("Choose a start value: "))
        end = int(input("Choose an end value: "))
        step = int(input("Choose a step value: "))

        if isinstance(name, str) and all(map(lambda t: isinstance(t, int), (initial, end, step))):
            Registry.register(name, cls(name=name, initial=initial, end=end, step=step))
            return Registry.get(name)
        else:
            print("Incompatible types", type(name), type(initial), type(end), type(step))
            return None

    def __repr__(self):
        return f"{type(self).__name__}(initial: {self.initial}, end: {self.end}, step: {self.step})"


class Numbers(Generator):
    pass
