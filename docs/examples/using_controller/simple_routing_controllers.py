from dmr.controller import Controller
from dmr.serializer import BaseSerializer


class UserList(Controller[BaseSerializer]):
    """UserList."""


class PostList(Controller[BaseSerializer]):
    """PostList."""


class UserDetail(Controller[BaseSerializer]):
    """UserDetail."""
