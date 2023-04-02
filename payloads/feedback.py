import math
import re
from payloads.payload import Payload, Registry


class Feedback(Payload):  # a payload that parses information from response body and uses it to compute the new request

    def __init__(self, name, initial):
        Payload.__init__(self, name)
        self.initial = initial
        self.end = -math.inf

    def next(self, response):
        if not response:
            return self.initial
        else:
            return self.compute(response)

    def done(self):
        return False

    def compute(self, response):
        pass

    @classmethod
    def setup(cls):
        pass


class RegExp(Feedback):

    def __init__(self, name, initial, expression, group):
        Feedback.__init__(self, name, initial)
        self.expression = re.compile(expression)
        self.group = group

    def compute(self, response):
        results = self.expression.search(response.text)
        return results[self.group]

    @classmethod
    def setup(cls):
        name = input("Choose a name for this payload: ")
        initial = input("Choose the initial value (to be used when there is no response yet): ")
        expression = input("Choose the regular expression to be used for extracting the payload data from the response: ")
        group = int(input("Choose the group number of the returned match that will be used for the payload: "))

        if isinstance(group, int) and all(map(lambda t: isinstance(t, str), (name, initial, expression))):
            Registry.register(name, cls(name=name, initial=initial, expression=expression, group=group))
            return Registry.get(name)
        else:
            print("Incompatible types", type(name), type(initial), type(expression), type(group))
            return None

    def __repr__(self):
        return f"{type(self).__name__}(initial: {self.initial}, expression: {self.expression}, group: {self.group})"
