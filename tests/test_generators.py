import unittest, argparse, os
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


class GeneratorTests(unittest.TestCase):

    @httpretty.activate
    def test_staggered(self):
        def request_callback(request, uri, response_headers, iterators=[0, 0]):
            assert request.headers["number1"] == str(iterators[0])
            assert request.headers["number2"] == str(iterators[1])
            iterators[0] = (iterators[0] + 1) % 5
            iterators[1] = (iterators[1] + 1) % 20

            return [200, response_headers, "testing numbers . . ."]

        httpretty.register_uri("GET", "https://cooky.test.com/staggered", body=request_callback)

        def mock_input(_, generator=input_generator("use headers number1 Numbers", "test_numbers1", "0", "4", "1",
                                                    "use headers number2 Numbers", "test_numbers2", "0", "19", "1")):
            return generator.__next__()

        mock_setup("https://cooky.test.com/staggered")
        arguments = argparse.ArgumentParser()
        arguments.shell = True

        with unittest.mock.patch("builtins.input", mock_input):
            main.cli(arguments)
            main.cli(arguments)
            main.execute()

        print(httpretty.last_request().headers["number1"])

        assert httpretty.last_request().headers["number1"] == "4"
        assert httpretty.last_request().headers["number2"] == "19"


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


class StringsTests(unittest.TestCase):
    def tearDown(self):
        for file in os.listdir("files"):
            os.remove(f"files/{file}")
        os.removedirs("files")

    def setUp(self):
        if "files" in os.listdir():
            for file in os.listdir("files"):
                os.remove(f"files/{file}")
            os.removedirs("files")
        os.mkdir("files")

    def test_setup(self):
        temp = open("files/temp.strings", "w")

        def mock_input(_, generator=input_generator("test", "files/temp.strings")):
            return generator.__next__()

        temp.writelines(["foo", "bar", "baz"])
        temp.close()

        with unittest.mock.patch("builtins.input", mock_input):
            self.assertIsNotNone(Strings.setup())

if __name__ == '__main__':
    unittest.main()
