from django_modern_rest.controller import Controller
from django_modern_rest.serializer import BaseSerializer


class UserList(Controller[BaseSerializer]):
    """UserList."""


class PostList(Controller[BaseSerializer]):
    """PostList."""


class UserDetail(Controller[BaseSerializer]):
    """UserDetail."""
