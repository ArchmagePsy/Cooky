import argparse
import json
import os
import pprint
import re
import sys
from io import BufferedReader
from operator import attrgetter

from pony.orm import db_session, select
from requests import request

from payloads.generator import Generator, Registry
from results import db
from results.models import Request, Response

printer = pprint.PrettyPrinter(indent=4)

requestMethod = "GET"

requestRoute = ""

requestBody = ""

requestParams = {
    "headers": {},
    "cookies": {},
    "params": {}
}

payloads = []

attributePattern = re.compile(r"([a-zA-Z]+) ([a-zA-Z\-]+) (.+)")
payloadPattern = re.compile(r"([a-zA-Z]+) ([a-zA-Z\-]+) ([A-Z]\w+)")


@db_session
def execute():
    payloads.sort(key=attrgetter("end"), reverse=True)

    if type(requestBody) is str:  # get the body as bytes
        request_data = requestBody.encode("utf-8")
    else:
        request_data = requestBody.read()
        requestBody.seek(0)  # go back to start of file

    while not payloads[0].done():

        request_params = dict()  # new params object for payloads

        for section in requestParams.keys():  # generate params with payload generators
            request_params[section] = {key: value.next() if isinstance(value, Generator) else value
                                       for key, value in requestParams[section].items()}

        # add request to db
        request_record = Request(method=requestMethod, route=requestRoute, headers=str(request_params["headers"]),
                                 cookies=str(request_params["cookies"]), params=str(request_params["params"]),
                                 data=request_data)

        db.commit()

        # make request
        response = request(requestMethod, requestRoute, data=requestBody, **request_params)

        # add response to db
        Response(request=request_record, route=response.url, headers=str(response.headers),
                 cookies=str(dict(response.cookies)), status=response.status_code, body=response.content)

        db.commit()

        for g in filter(lambda p: p.done(), payloads[1:]):
            g.reset()

    return True


@db_session
def cli(args):
    global requestBody, requestRoute, requestMethod, requestParams, payloads

    if args.shell:  # start interactive shell
        command = input("> ")

        if (arg_command := command[:3].upper()) == "SET":  # set attributes in sections or arguments
            match = attributePattern.match(command[3:].strip())

            if not match:
                return True

            section, key, value = match[1], match[2], match[3]

            if section.upper() == "REQUEST":  # setting a request argument
                if (argument := key.upper()) == "METHOD":  # set the method
                    requestMethod = value
                elif argument == "ROUTE":  # set the route
                    requestRoute = value
                elif argument == "BODY":  # set the body
                    requestBody = open(value, "rb") if os.path.isfile(value) else value
                else:
                    print(f"No request argument '{key}'")
            elif section in requestParams.keys():  # set one of the parameter sections
                requestParams[section][key] = value
            else:
                print(f"No section '{section}'")
        elif arg_command == "USE":
            match = payloadPattern.match(command[3:].strip())

            if not match:
                return True

            section, key, payload = match[1], match[2], match[3]

            if section in requestParams.keys():  # set one of the parameter sections to given payload
                generator = Registry.get(payload)

                if not generator:
                    print(f"No payload '{payload}'")

                payloads.append(generator)
                requestParams[section][key] = generator
            else:
                print(f"No section '{section}'")
        elif (single_command := command.upper()) == "VIEW":  # print the request parameters
            print(f"{requestMethod}\t{requestRoute}")
            printer.pprint(requestParams)
            print(requestBody)
        elif single_command == "RESULTS":  # print the results
            select((res.id, res.route, res.status, req.method, req.route)
                   for res in Response for req in Request).show(width=100)
        elif single_command == "RUN":
            return False
        elif single_command == "QUIT":
            sys.exit(0)
    else:
        return False

    return args.shell


def main(args):  # run the program
    while cli(args):
        pass

    return execute()


def setup():
    global requestMethod, requestRoute
    parser = argparse.ArgumentParser()

    parser.add_argument("-r", help="set route for the request", type=str, dest="route")
    parser.add_argument("-m", help="set method to use for the request",
                        choices=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
                        default="GET", dest="method")
    parser.add_argument("-i", help="open up interactive shell", action="store_true", dest="shell")
    parser.add_argument("-j", help="import parameters from a JSON file", dest="json_file")

    arguments = parser.parse_args()

    # set method and route from args
    requestMethod = arguments.method
    requestRoute = arguments.route

    if arguments.json_file:  # load json into params
        with open(arguments.json_file, "rb") as file:
            requestParams.update(**json.load(file))

    db.generate_mapping(create_tables=True)  # setup db

    return arguments


def cleanup():
    if isinstance(requestBody, BufferedReader):  # close file object if created
        requestBody.close()


if __name__ == "__main__":

    arguments = setup()

    while main(arguments):
        pass

    cleanup()
