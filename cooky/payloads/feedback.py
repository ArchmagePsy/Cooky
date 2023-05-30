import math
import re
from cooky.payloads.payload import Payload, Registry


class Feedback(Payload):  # a payload that parses information from response body and uses it to compute the new request

    def __init__(self, name, initial):
        """
        Base class for Feedback payloads, these payloads compute the input for the request based on some
        information in the response
        :param name: name for the payload
        :param initial: the initial value for when there is not yet a response to compute a request for
        """
        Payload.__init__(self, name)
        self.initial = initial
        self.end = -math.inf

    def next(self, response):
        """
        Returns the next payload value, initial if response is empty otherwise reponse is used to compute the next item
        :param response: the response object recieved from the previous request
        :return: the next payload value
        """
        if not response:
            return self.initial
        else:
            return self.compute(response)

    def done(self):
        """
        Overrides parent, returns whether or not the payload has run out of values. Always returns False
        :return:
        """
        return False

    def compute(self, response):
        """
        Computes next value based on response, empty in base so must be overridden by children
        :param response: response to the previous request
        """
        pass

    @classmethod
    def setup(cls):
        """
        This classmethod implements a way to instantiate payloads via the commandline, is empty by default in the base
        and must be overridden
        """
        pass


class RegExp(Feedback):

    def __init__(self, name, initial, expression, group):
        """
        This payload inherits from Feedback and computes the next item by extracting it from the response using a
        regular expression
        :param name: name for the payload
        :param initial: initial value when no response is present
        :param expression: regular expression used to extract value from response
        :param group: number of the group in the regular expression to use as the value
        """
        Feedback.__init__(self, name, initial)
        self.expression = re.compile(expression)
        self.group = group

    def compute(self, response):
        """
        Computes the value by extracting it from the previous response with a regular expression
        :param response: response to the previous request
        :return: payload value
        """
        results = self.expression.search(response.text)
        return results[self.group]

    @classmethod
    def setup(cls):
        """
        Classmethod facilitating interactive setup of the RegExp payload, see constructor for input values
        :return: if all inputs are valid it returns a RegExp payload, otherwise None
        """
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
