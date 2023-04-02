import main

def input_generator(*inputs):
    for s in inputs: yield s


def mock_setup(route):
    main.requestMethod = "GET"
    main.requestRoute = route
    main.payloads = []
    main.requestParams = {
        "headers": {},
        "cookies": {},
        "params": {}
    }

    if not main.db.schema:
        main.db.generate_mapping(create_tables=True)