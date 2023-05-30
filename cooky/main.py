import argparse
import importlib
import json
import os
import pprint
import re
import sys
from io import BufferedReader
from operator import attrgetter
from textwrap import wrap

from pony.orm import db_session, select
from requests import request
from tabulate import tabulate

from cooky.payloads import generator, feedback
from cooky.payloads.generator import Generator
from cooky.payloads.feedback import Feedback
from cooky.results import db
from cooky.results.models import Request, Response, Payload

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

payloads_list = []
payload_modules = [generator, feedback]

attributePattern = re.compile(r"([a-zA-Z]+) ([a-zA-Z][a-zA-Z0-9\-]*) (.+)")
deletePattern = re.compile(r"([a-zA-Z]+) ([a-zA-Z][a-zA-Z0-9\-]*)")
payloadPattern = re.compile(r"([a-zA-Z]+) ([a-zA-Z][a-zA-Z0-9\-]*) ([A-Z]\w+)")
packagePattern = re.compile(r"([a-zA-Z.]+) from ([a-zA-Z.]+)")


@db_session
def execute(tryout=None):
    """
    This function executes the payloads and makes the requests, if no payloads have been registered then a single request
    with the specified parameters will be made
    :param tryout: an optional argument set to None by default, controls the number of requests that will be retried if
                the payload would otherwise run indefinitely (in the case of a feedback payload for example)
    :return: always returns True
    """
    global requestMethod, requestRoute, requestAuth, requestBody, requestParams, packagePattern, payloadPattern, attributePattern, payloads_list, payload_modules
    payloads_list.sort(key=attrgetter("end"), reverse=True)

    if type(requestBody) is str:  # get the body as bytes
        request_data = requestBody.encode("utf-8")
    else:
        request_data = requestBody.read()
        requestBody.seek(0)  # go back to start of file

    if payloads_list:

        response = None
        tries = 0

        while (not payloads_list[0].done() and tryout is None) or (tryout is not None and tries < tryout):

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
                        request_params[section][key] = value.next(response) if section == "params" else str(
                            value.next(response))
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

            tries += 1

            for g in filter(lambda p: p.done(), payloads_list[1:]):
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
    """
    runs the interactive command shell that allows the user to customize parts of the request and setup payloads used in
    different sections. Once a user is done they can run the payload and comb through its results with the commandline
    search functionality
    :param args: argumentParser object necessary to determine of shell should be run
    :return: returns False if requests should be executed and True otherwise
    """
    global requestMethod, requestRoute, requestAuth, requestBody, requestParams, packagePattern, payloadPattern, attributePattern, payloads_list, payload_modules
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
                payload_klass = None

                for module in payload_modules:
                    payload_klass = getattr(module, payload, None)

                    if payload_klass:
                        break

                if not payload_klass or payload == "Registry":
                    print(f"No payload '{payload}'")
                    return True
                if payload_config := payload_klass.setup():  # setup the payload and insert it if successful
                    payloads_list.append(payload_config)
                    requestParams[section][key] = payload_config
            else:
                print(f"No section '{section}'")
        elif arg_command == "DEL":
            match = deletePattern.match(command[3:].strip())

            if not match:
                return True

            section, key = match[1], match[2]

            if section.upper() == "REQUEST":  # deleting a request argument
                if (argument := key.upper()) == "BODY": # delete the body
                    requestBody = ""
                else:
                    print(f"No request argument or could not remove '{key}'")
            elif section in requestParams.keys():  # delete one of the parameter sections
                if key in requestParams[section].keys(): del requestParams[section][key]
                else: print(f"No field '{key}' in  '{section}'")
            else:
                print(f"No section '{section}'")
        elif arg_command == "MOD":
            match = packagePattern.match(command[3:].strip())
            try:
                module = importlib.import_module(match[1], match[2])
                payload_modules.append(module)
            except ModuleNotFoundError:
                print(f"No such module '{match[1]}'")

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
            for p in payloads_list:
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

    return execute(args.tryout)


def setup():
    """
    Sets up the argumentParser and reads setting in from json file to setup the initial state of the request, also sets up
    the database
    :return: returns the argumentParser object for use in main
    """
    global requestMethod, requestRoute, requestParams
    parser = argparse.ArgumentParser()

    parser.add_argument("-r", help="set route for the request", type=str, dest="route")
    parser.add_argument("-m", help="set method to use for the request",
                        choices=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
                        default="GET", dest="method")
    parser.add_argument("-t", help="number of iterations to execute the "
                                   "payloads for, useful when payloads otherwise run "
                                   "indefinitely", default=None, type=int, dest="tryout")
    parser.add_argument("-i", help="open up interactive shell", action="store_true", dest="shell")
    parser.add_argument("-j", help="import parameters from a JSON file", dest="json_file")

    arguments = parser.parse_args()

    if not arguments.shell and (not all([arguments.route, arguments.method]) and not arguments.json_file):
        parser.print_help()
        print("route and method required in non-interactive mode")
        sys.exit(0)

    # set method and route from args
    requestMethod = arguments.method
    requestRoute = arguments.route

    if arguments.json_file:  # load json into params
        with open(arguments.json_file, "rb") as file:
            requestParams.update(**json.load(file))

    db.generate_mapping(create_tables=True)  # setup db

    return arguments


def cleanup():
    """
    cleanup for the program, closes file stream if opened for request body
    """
    global requestBody
    if isinstance(requestBody, BufferedReader):  # close file object if created
        requestBody.close()


def exe():
    arguments = setup()

    while main(arguments):
        pass

    cleanup()


if __name__ == "__main__":
    exe()
