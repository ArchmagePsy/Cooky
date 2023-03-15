"""
CHANGES MADE: added support for more general payload types, organised imports, added feedback type

TODO: testing, write unittests for EVERY payload type and make sure that changes to payload system are compatible
    potentially look into setting up a test service, look into turning this into a command (like cooky -i instead of python main.py -i),
    also once more payload options and documentation has been written create a python package

DONE: tests for Generators and Numbers
TODO: test Strings and Feedback (RegExp)

DON'T FORGET TO COMMIT CHANGES ONCE TESTED
"""


import argparse, json, os, pprint, re, sys
from io import BufferedReader
from operator import attrgetter
from textwrap import wrap

from pony.orm import db_session, select
from requests import request
from tabulate import tabulate

from payloads import generator, feedback
from payloads.feedback import Feedback
from payloads.generator import Generator
from results import db
from results.models import Request, Response, Payload

printer = pprint.PrettyPrinter(indent=4)

requestMethod = "GET"

requestRoute = ""

requestBody = ""

requestParams = {
    "headers": {},
    "cookies": {},
    "params": {}
}

requestAuth = None

payloads = []

attributePattern = re.compile(r"([a-zA-Z]+) ([a-zA-Z][a-zA-Z0-9\-]+) (.+)")
payloadPattern = re.compile(r"([a-zA-Z]+) ([a-zA-Z][a-zA-Z0-9\-]+) ([A-Z]\w+)")


@db_session
def execute():
    payloads.sort(key=attrgetter("end"), reverse=True)

    if type(requestBody) is str:  # get the body as bytes
        request_data = requestBody.encode("utf-8")
    else:
        request_data = requestBody.read()
        requestBody.seek(0)  # go back to start of file

    if payloads:

        response = None

        while not payloads[0].done():

            request_params = {
                "headers": {},
                "cookies": {},
                "params": {}
            }  # new params object for payloads

            payload_records = []

            for section in requestParams.keys():  # generate params with payload generators
                for key, value in requestParams[section].items():

                    if isinstance(value, Generator):
                        request_params[section][key] = value.next() if section == "params" else str(value.next())
                        payload_records.append(Payload(value=str(request_params[section][key]), name=value.name))
                    elif isinstance(value, Feedback):
                        request_params[section][key] = value.next(response) if section == "params" else str(value.next(response))
                        payload_records.append(Payload(value=str(request_params[section][key]), name=value.name))
                    else:
                        request_params[section][key] = value

            # add request to db
            request_record = Request(method=requestMethod, route=requestRoute, headers=str(request_params["headers"]),
                                     cookies=str(request_params["cookies"]), params=str(request_params["params"]),
                                     payloads=payload_records, data=request_data)

            db.commit()

            # make request
            response = request(requestMethod, requestRoute, data=requestBody, auth=requestAuth, **request_params)

            # add response to db
            Response(request=request_record, route=response.url, headers=str(response.headers),
                     cookies=str(dict(response.cookies)), status=response.status_code, body=response.content,
                     encoding=response.encoding)

            db.commit()

            for g in filter(lambda p: p.done(), payloads[1:]):
                g.reset()
    else:
        # add request to db
        request_record = Request(method=requestMethod, route=requestRoute, headers=str(requestParams["headers"]),
                                 cookies=str(requestParams["cookies"]), params=str(requestParams["params"]),
                                 data=request_data)

        db.commit()

        # make request
        response = request(requestMethod, requestRoute, data=requestBody, **requestParams)

        # add response to db
        Response(request=request_record, route=response.url, headers=str(response.headers),
                 cookies=str(dict(response.cookies)), status=response.status_code, body=response.content,
                 encoding=response.encoding)

        db.commit()

    return True


@db_session
def cli(args):
    global requestBody, requestRoute, requestMethod, requestParams, requestAuth, payloads

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
                payload_klass = getattr(generator, payload, None)
                if not payload_klass: payload_klass = getattr(feedback, payload, None)

                if not payload_klass or payload == "Registry":
                    print(f"No payload '{payload}'")
                    return True
                if payload_config := payload_klass.setup():  # setup the payload and insert it if successful
                    payloads.append(payload_config)
                    requestParams[section][key] = payload_config
            else:
                print(f"No section '{section}'")
        elif arg_command == "GET":
            res = Response[int(command[3:].strip())]
            newline = "\n"

            print(f"URL: {res.route}",
                  f"status: {res.status}",
                  f"headers: {newline.join(wrap(res.headers, width=100))}",
                  f"cookies: {newline.join(wrap(res.cookies, width=100))}",
                  res.body.decode(res.encoding), sep="\n")
        elif (single_command := command.upper()) == "VIEW":  # print the request parameters
            print(f"{requestMethod}\t{requestRoute}")
            printer.pprint(requestParams)
            print(requestBody)
        elif single_command == "AUTH":
            username = input("Enter username: ")
            password = input("Enter password: ")

            requestAuth = (username, password)
        elif single_command == "RESULTS":  # print the results
            filter_regex = input("filter?> ")

            query = select((res, req)
                           for res in Response for req in Request
                           if res.request == req)

            data = []

            for res, req in query:
                row = [req.id, req.method, req.route, res.route, f"{len(res.body)} bytes", res.status]
                row.extend(map(attrgetter("value"), sorted(req.payloads, key=attrgetter("name"))))

                if filter_regex.strip() == "" or re.search(filter_regex, res.body.decode(res.encoding)):
                    data.append(row)

            headers = ["id", "method", "request-url", "response-url", "response-size", "status"]
            headers.extend(f"Payload {name}" for name in sorted(map(attrgetter("name"), query.first()[1].payloads)))

            print(tabulate(data, headers=headers))

        elif single_command == "RUN":
            for p in payloads:
                p.reset()
            return False
        elif single_command == "QUIT":
            sys.exit(0)
        else:
            print("Unrecognised expression:", command)
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
