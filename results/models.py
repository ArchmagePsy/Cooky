from pony.orm import Optional, Required, LongStr, Set

from results import db


class Payload(db.Entity):
    request = Optional("Request")
    name = Required(str)
    value = Required(LongStr)


class Request(db.Entity):
    response = Optional("Response")
    method = Required(str)
    route = Required(str)
    headers = Required(LongStr)
    cookies = Required(LongStr)
    params = Required(LongStr)
    payloads = Set("Payload")
    data = Required(bytes)


class Response(db.Entity):
    request = Required("Request")
    route = Required(str)
    headers = Required(LongStr)
    cookies = Required(LongStr)
    encoding = Required(str)
    body = Required(bytes)
    status = Required(int)
