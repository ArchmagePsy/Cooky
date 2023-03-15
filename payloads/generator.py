import os
from payloads.payload import Payload, Registry


class Generator(Payload):

    def __init__(self, name, initial, end, step):
        Payload.__init__(self, name)
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


class Strings(Generator):

    def __init__(self, name, strings, file, initial, end, step):
        Generator.__init__(self, name, initial, end, step)
        self.strings = strings
        self.file = file

    def generate(self):
        return self.strings[self.count]

    @classmethod
    def setup(cls):
        name = input("Choose a name for this payload: ")
        file = input("Choose a file path for strings: ")

        if not isinstance(name, str) or not os.path.isfile(file):
            print("File not found or name not valid")
            return None

        string_file = open(file, "r")
        strings = [string for string in string_file.read().splitlines()]
        string_file.close()
        initial = 0
        end = len(strings) - 1
        step = 1

        Registry.register(name, cls(name=name, strings=strings, file=file, initial=initial, end=end, step=step))
        return Registry.get(name)

    def __repr__(self):
        return f"{type(self).__name__}(file: {self.file})"
