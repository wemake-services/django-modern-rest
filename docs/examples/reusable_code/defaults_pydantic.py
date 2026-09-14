from examples.reusable_code.reusable_defaults import ReusableController


class PydanticController(ReusableController):
    """Both the serializer and the request model are taken from defaults."""


# run: {"controller": "PydanticController", "method": "post", "body": {"first_name": "Nikita", "last_name": "Sobolev"}, "url": "/api/example/"}  # noqa: ERA001, E501
# openapi: {"controller": "PydanticController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
