class Registry:
    payloads = {}

    @classmethod
    def register(cls, name, payload):
        if isinstance(payload, Payload):
            cls.payloads[name] = payload
        else:
            raise TypeError(f"{type(payload)} is not compatible")

    @classmethod
    def get(cls, name):
        return cls.payloads[name]


class Payload:
    def __init__(self, name):
        self.name = name

    def next(self):
        pass

    def reset(self):
        pass

    def done(self):
        pass

    @classmethod
    def setup(cls):
        name = input("Choose a name for this payload: ")

        if isinstance(name, str):
            Registry.register(name, cls(name=name))
            return Registry.get(name)
        else:
            print("Incompatible type", type(name))
            return None

    def __repr__(self):
        return f"{type(self).__name__}"
