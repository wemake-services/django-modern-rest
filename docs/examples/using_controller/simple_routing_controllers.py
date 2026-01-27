from django_modern_rest.controller import Controller
from django_modern_rest.serialization import BaseSerializer


class UserList(Controller[BaseSerializer]):
    """UserList."""


class PostList(Controller[BaseSerializer]):
    """PostList."""


class UserDetail(Controller[BaseSerializer]):
    """UserDetail."""
