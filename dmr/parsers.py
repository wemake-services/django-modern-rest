import abc
import json
from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeAlias, final

from django.core.exceptions import BadRequest, TooManyFilesSent
from django.http import HttpRequest
from django.http.multipartparser import MultiPartParserError
from typing_extensions import override

from dmr.exceptions import DataParsingError, RequestSerializationError
from dmr.internal.django import parse_as_post
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer

#: Types that are possible to load json from.
Raw: TypeAlias = str | bytes | bytearray


#: Type that represents the `deserializer` hook.
DeserializeFunc: TypeAlias = Callable[[type[Any], Any], Any]


class Parser(ResponseSpecProvider):
    """
    Base class for all parsers.

    Subclass it to implement your own parsers.
    """

    __slots__ = ()

    content_type: str
    """
    Content-Type that this parser works with.

    Must be defined for all subclasses.
    """

    @abc.abstractmethod
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        """
        Deserialize a raw string/bytes/bytearray into an object.

        Args:
            to_deserialize: Value to deserialize.
            deserializer_hook: Hook to convert types
                that are not natively supported.
            request: Django's original request with all the details.
            model: Model that reprensents the final result's structure.

        Raises:
            DataParsingError: If error decoding ``obj``.

        Returns:
            Simple python object with primitive parts.

        """

    @override
    @classmethod
    def provide_response_specs(
        cls,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when data can't be parsed."""
        # We don't provide parser errors by default, because parser only works
        # when there are active components. But, components already provide
        # required response specs. This method is only useful
        # for custom user-defined errors.
        return []


class JsonParser(Parser):
    """
    Fallback implementation of a json parser.

    Only is used when ``msgspec`` is not installed.

    .. warning::

        It is not recommended to be used directly.
        It is slow and has less features.
        We won't add any complex objects support to this parser.

    """

    __slots__ = ()

    content_type = 'application/json'
    """Works with ``json`` only."""

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        """
        Decode a JSON string/bytes/bytearray into an object.

        Args:
            to_deserialize: Value to decode.
            deserializer_hook: Hook to convert types
                that are not natively supported.
            request: Django's original request with all the details.
            model: Model that reprensents the final result's structure.

        Raises:
            DataParsingError: If error decoding ``obj``.

        Returns:
            Decoded object.

        """
        try:
            return json.loads(to_deserialize)
        except (ValueError, TypeError) as exc:
            # Corner case: when deserializing an empty body,
            # return `None` instead.
            # We do this here, because we don't want
            # a penalty for all positive cases.
            if to_deserialize == b'':
                return None
            raise DataParsingError(str(exc)) from exc


class SupportsFileParsing:
    """
    Mixin class for parsers that can parse files.

    We require parsers that can parse files to populate
    :attr:`django.http.HttpRequest.FILES` and to not return anything.
    """

    @abc.abstractmethod
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> None:
        """Populate ``request.FILES`` if possible."""


class SupportsDjangoDefaultParsing:
    """
    Mark for parsers that support default Django's parsing.

    By default Django can parse `multipart/form-data`
    and `application/x-www-form-urlencoded` in a very specific way.
    Django only parses :attr:`django.http.HttpRequest.POST`
    and :attr:`django.http.HttpRequest.FILES`
    when it receives a real ``POST`` request.
    Which does not really work for us.
    We need more methods to be able to send the same content.

    So, parsers that extends this type must:
    1. Return default parsed objects when method is ``POST``
    2. Parse similar HTTP methods the same way Django does for ``POST``

    Contract: ``parse()`` method must return ``None``, but populate
    :attr:`django.http.HttpRequest.POST`
    and :attr:`django.http.HttpRequest.FILES` if they were missing.
    """

    @abc.abstractmethod
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> None:
        """Populate ``request.POST`` and ``request.FILES`` if possible."""


class MultiPartParser(
    SupportsFileParsing,
    SupportsDjangoDefaultParsing,
    Parser,
):
    """
    Parses multipart form data.

    In reallity this is a quite tricky parser.
    Since, Django already parses ``multipart/form-data`` content natively,
    there's no reason to duplicate its work.
    So, we return original Django's content.
    """

    content_type = 'multipart/form-data'
    """Works with multipart data."""

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> None:
        """Returns parsed multipart form data."""
        # Circular import:
        from dmr.settings import (  # noqa: PLC0415
            Settings,
            resolve_setting,
        )

        if (
            not getattr(request, '_dmr_parsed_as_post', False)
            and request.method
            and (
                request.method.upper()
                in resolve_setting(Settings.django_treat_as_post)
            )
        ):
            # By default django only parses `POST` methods.
            # This is a long-standing feature, not a bug.
            # https://code.djangoproject.com/ticket/12635
            # So, we trick django to parse non-POST method as real POST methods.
            parse_as_post(request)

        try:
            # We need to force django to evaluate the request's body now.
            # So, any errors that will happen will happen here.
            request.POST, request.FILES  # noqa: B018  # pyright: ignore[reportUnusedExpression]
        except (MultiPartParserError, TooManyFilesSent) as exc:
            raise RequestSerializationError(str(exc)) from None
        # It is already parsed by Django itself, no need to return anything.


class FormUrlEncodedParser(
    SupportsDjangoDefaultParsing,
    Parser,
):
    """
    Parses www urlencoded forms.

    In reallity this is a quite tricky parser.
    Since, Django already parses ``application/x-www-form-urlencoded``
    content natively, there's no reason to duplicate its work.
    So, we return original Django's content.
    """

    content_type = 'application/x-www-form-urlencoded'
    """Works with urlencoded forms."""

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> None:
        """Returns parsed form data."""
        # Circular import:
        from dmr.settings import (  # noqa: PLC0415
            Settings,
            resolve_setting,
        )

        if (
            not getattr(request, '_dmr_parsed_as_post', False)
            and request.method
            and (
                request.method.upper()
                in resolve_setting(Settings.django_treat_as_post)
            )
        ):
            # By default django only parses `POST` methods.
            # This is a long-standing feature, not a bug.
            # https://code.djangoproject.com/ticket/12635
            # So, we trick django to parse non-POST method as real POST methods.
            parse_as_post(request)

        try:
            # We need to force django to evaluate the request's body now.
            # So, any errors that will happen will happen here.
            request.POST  # noqa: B018
        except BadRequest as exc:
            raise RequestSerializationError(str(exc)) from None
        # It is already parsed by Django itself, no need to return anything.


@final
class _NoOpParser(Parser):  # pyright: ignore[reportUnusedClass]
    __slots__ = ('content_type',)

    def __init__(self, content_type: str) -> None:
        self.content_type = content_type

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        raise NotImplementedError('NoOpParser.parse() should not be used')
