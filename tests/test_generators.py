import unittest, argparse
import unittest.mock

import httpretty
from payloads.generator import Numbers, Strings
import main


def input_generator(*inputs):
    for s in inputs: yield s


def mock_setup(route):
    main.requestMethod = "GET"
    main.requestRoute = route

    main.db.generate_mapping(create_tables=True)


class NumbersTests(unittest.TestCase):
    def test_setup(self):
        def mock_input(_, generator=input_generator("test", "0", "10", "1")):
            return generator.__next__()

        with unittest.mock.patch("builtins.input", mock_input):
            self.assertIsNotNone(Numbers.setup())

    @httpretty.activate
    def test_execute(self):
        def request_callback(request, uri, response_headers, iterators=[0]):
            assert request.headers["number"] == str(iterators[0])
            iterators[0] += 1

            return [200, response_headers, "testing numbers . . ."]

        httpretty.register_uri("GET", "https://cooky.test.com/numbers", body=request_callback)

        def mock_input(_, generator=input_generator("use headers number Numbers", "test_numbers", "0", "10", "1")):
            return generator.__next__()

        mock_setup("https://cooky.test.com/numbers")
        arguments = argparse.ArgumentParser()
        arguments.shell = True

        with unittest.mock.patch("builtins.input", mock_input):
            main.cli(arguments)
            main.execute()

        assert httpretty.last_request().headers["number"] == "10"


if __name__ == '__main__':
    unittest.main()
