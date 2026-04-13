from typing import TYPE_CHECKING, Generic, TypeVar

from django.http import HttpRequest

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser


_UserT = TypeVar('_UserT', bound='AbstractBaseUser')


class AuthenticatedHttpRequest(HttpRequest, Generic[_UserT]):
    """
    Annotation for requests that used auth.

    Use it for trusted controllers only.
    """

    user: _UserT  # pyright: ignore[reportIncompatibleVariableOverride]  # pyrefly: ignore[bad-override]
