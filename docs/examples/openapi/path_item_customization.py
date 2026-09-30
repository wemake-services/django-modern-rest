from dmr import Controller
from dmr.openapi.objects import ExternalDocumentation, Server
from dmr.plugins.msgspec import MsgspecSerializer


class UserController(Controller[MsgspecSerializer]):
    """
    Users API.

    Replaced description.
    """  # This docstring becomes the `summary`, but not `description`

    description = 'Create new users'  # Set explicitly, not from the docstring
    servers = (
        Server(url='https://example.com'),
        Server(url='https://dev.example.com'),
    )
    # These are used for all operations, unless an endpoint sets its own:
    deprecated = True
    external_docs = ExternalDocumentation(url='https://example.com/docs')

    def post(self) -> str:
        return 'post'


# openapi: {"controller": "UserController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
