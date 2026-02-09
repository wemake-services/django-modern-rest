from abc import abstractmethod
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, Generic, TypeVar

from django.conf import settings
from django.contrib.auth import aauthenticate, alogin, authenticate, login
from typing_extensions import TypedDict

from django_modern_rest import (
    Body,
    Controller,
    CookieSpec,
    ResponseSpec,
    modify,
)
from django_modern_rest.errors import ErrorModel
from django_modern_rest.exceptions import NotAuthenticatedError
from django_modern_rest.serializer import BaseSerializer

_RequestModelT = TypeVar('_RequestModelT', bound=Mapping[str, Any])
_ResponseT = TypeVar('_ResponseT')
_SerializerT = TypeVar(
    '_SerializerT',
    bound=BaseSerializer,
)


class DjangoSessionPayload(TypedDict):
    """
    Payload for default version of a django session request body.

    Is also used as kwargs for :func:`django.contrib.auth.authenticate`.
    """

    username: str
    password: str


class DjangoSessionResponse(TypedDict):
    """Default response type for django session endpoint."""

    user_id: str


class DjangoSessionSyncController(
    Controller[_SerializerT],
    Body[_RequestModelT],
    Generic[_SerializerT, _RequestModelT, _ResponseT],
):
    """
    Sync controller to get django session cookie.

    See also:
        https://docs.djangoproject.com/en/6.0/topics/auth/

    """

    responses = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @modify(
        status_code=HTTPStatus.OK,
        cookies={settings.SESSION_COOKIE_NAME: CookieSpec(schema_only=True)},
    )
    def post(self) -> _ResponseT:
        """By default cookies are acquired on post."""
        return self.login()

    def login(self) -> _ResponseT:
        """Perform the sync login routine for user."""
        user = authenticate(
            self.request,
            **self.convert_auth_payload(self.parsed_body),
        )
        if user is None:
            raise NotAuthenticatedError
        login(self.request, user)
        return self.make_api_response()

    @abstractmethod
    def convert_auth_payload(
        self,
        payload: _RequestModelT,
    ) -> DjangoSessionPayload:
        """
        Convert your custom payload to kwargs that django supports.

        See :func:`django.contrib.auth.authenticate` docs
        on which kwargs it supports.

        Basically it needs ``username`` and ``password`` strings.
        """
        raise NotImplementedError

    @abstractmethod
    def make_api_response(self) -> _ResponseT:
        """Abstract method to create a response payload."""
        raise NotImplementedError


class DjangoSessionAsyncController(
    Controller[_SerializerT],
    Body[_RequestModelT],
    Generic[_SerializerT, _RequestModelT, _ResponseT],
):
    """
    Async controller to get django session cookie.

    See also:
        https://docs.djangoproject.com/en/6.0/topics/auth/

    """

    responses = (
        ResponseSpec(
            return_type=ErrorModel,
            status_code=HTTPStatus.UNAUTHORIZED,
        ),
    )

    @modify(
        status_code=HTTPStatus.OK,
        cookies={settings.SESSION_COOKIE_NAME: CookieSpec(schema_only=True)},
    )
    async def post(self) -> _ResponseT:
        """By default cookies are acquired on post."""
        return await self.login()

    async def login(self) -> _ResponseT:
        """Perform the sync login routine for user."""
        user = await aauthenticate(
            self.request,
            **(await self.convert_auth_payload(self.parsed_body)),
        )
        if user is None:
            raise NotAuthenticatedError
        await alogin(self.request, user)
        return await self.make_api_response()

    @abstractmethod
    async def convert_auth_payload(
        self,
        payload: _RequestModelT,
    ) -> DjangoSessionPayload:
        """
        Convert your custom payload to kwargs that django supports.

        See :func:`django.contrib.auth.authenticate` docs
        on which kwargs it supports.

        Basically it needs ``username`` and ``password`` strings.
        """
        raise NotImplementedError

    @abstractmethod
    async def make_api_response(self) -> _ResponseT:
        """Abstract method to create a response payload."""
        raise NotImplementedError
