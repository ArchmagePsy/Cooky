from pony.orm import Optional, Required, LongStr

from results import db


class Request(db.Entity):
    response = Optional("Response")
    method = Required(str)
    route = Required(str)
    headers = Required(LongStr)
    cookies = Required(LongStr)
    params = Required(LongStr)
    data = Required(bytes)


class Response(db.Entity):
    request = Required("Request")
    route = Required(str)
    headers = Required(LongStr)
    cookies = Required(LongStr)
    body = Required(bytes)
    status = Required(int)