import os
from cooky.payloads.payload import Payload, Registry


class Generator(Payload):

    def __init__(self, name, initial, end, step):
        """
        Base class for a generator payload, this type of payload iterates through a set of values be it numbers of strings.
        (The Generator base class implements all the features necessary for the Numbers payload)
        :param name: name of the payload
        :param initial: the initial value
        :param end: the final value
        :param step: the step that the values should increment in (if decreasing payload is desired use negative step)
        """
        Payload.__init__(self, name)
        self.initial = initial
        self.count = initial
        self.step = step
        self.end = end

    def next(self):
        """
        Returns the next value for the payload by generating it and then incrementing the count by the defined step
        :return: the next payload value
        """
        payload = self.generate()
        self.count += self.step
        return payload

    def reset(self):
        """
        Rewinds the count for the generator back to the initial value so it can be restarted or looped
        """
        self.count = self.initial

    def done(self):
        """
        Determines if the generator has any more values to generate (if the count is greater than the end)
        :return: True if there are no more values and False if there are
        """
        return self.count > self.end

    def generate(self):
        """
        Generates the current value for the payload
        :return: the count
        """
        return self.count

    @classmethod
    def setup(cls):
        """
        Classmethod facilitating interactive setup of the Numbers payload, see Generator constructor for input values
        :return: if all inputs are valid it returns a Generator or Numbers payload, otherwise None
        """
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
        """
        This payload inherits Generator and generates string values from a 
        :param name:
        :param strings:
        :param file:
        :param initial:
        :param end:
        :param step:
        """
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

        string_file = open(file, "r", newline="\n")
        strings = [string for string in string_file.read().splitlines()]
        string_file.close()
        initial = 0
        end = len(strings) - 1
        step = 1

        Registry.register(name, cls(name=name, strings=strings, file=file, initial=initial, end=end, step=step))
        return Registry.get(name)

    def __repr__(self):
        return f"{type(self).__name__}(file: {self.file})"
