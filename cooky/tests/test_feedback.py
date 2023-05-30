import argparse
import unittest
import unittest.mock

import httpretty

from cooky import main
from cooky.payloads.feedback import RegExp
from cooky.tests import input_generator, mock_setup


class RegExpTests(unittest.TestCase):
    def test_setup(self):
        def mock_input(_, generator=input_generator("test", "none", "feed=(.+)", "1")):
            return generator.__next__()

        with unittest.mock.patch("builtins.input", mock_input):
            self.assertIsNotNone(RegExp.setup())

    @httpretty.activate()
    def test_execute(self):
        def request_callback(request, uri, response_headers, iterators=[0]):
            assert request.headers["back"] == "none" or request.headers["back"] == str(iterators[0])
            iterators[0] += 1

            return [200, response_headers, "testing RegExp . . . feed=" + str(iterators[0])]

        httpretty.register_uri("GET", "https://cooky.test.com/regexp", body=request_callback)

        def mock_input(_,
                       generator=input_generator("use headers back RegExp", "test_regexp", "none", "feed=(.+)", "1")):
            return generator.__next__()

        mock_setup("https://cooky.test.com/regexp")
        arguments = argparse.ArgumentParser()
        arguments.shell = True

        with unittest.mock.patch("builtins.input", mock_input):
            main.cli(arguments)
            main.execute(tryout=10)


if __name__ == '__main__':
    unittest.main()
