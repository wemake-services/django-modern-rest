import abc
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from django.http import HttpRequest
from typing_extensions import override

from django_modern_rest.exceptions import (
    DataParsingError,
    RequestSerializationError,
)
from django_modern_rest.response import ResponseDescription
from django_modern_rest.serialization import BaseSerializer

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint

_QueryT = TypeVar('_QueryT')
_BodyT = TypeVar('_BodyT')
_HeadersT = TypeVar('_HeadersT')
_PathT = TypeVar('_PathT')
_CookiesT = TypeVar('_CookiesT')


class ComponentParser:
    """Base abstract provider for request components."""

    # Public API:
    context_name: ClassVar[str]

    # Internal API:
    __is_base_type__: ClassVar[bool] = True

    @classmethod
    @abc.abstractmethod
    def provide_context_data(
        cls,
        blueprint: 'Blueprint[BaseSerializer]',
        model: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Return unstructured raw value for serializer.from_python().

        Implement body JSON decoding / content-type checks here if needed.
        """
        raise NotImplementedError

    @classmethod
    def provide_responses(
        cls,
        serializer: type[BaseSerializer],
        model: Any,
    ) -> list[ResponseDescription]:
        """
        Return a list of extra responses that this component produces.

        For example, when parsing something, we always have an option
        to fail a parsing, if some request does not fit our model.
        """
        return [
            ResponseDescription(
                # We do this for runtime validation, not static type check:
                serializer.response_parsing_error_model,
                status_code=RequestSerializationError.status_code,
            ),
        ]


class Query(ComponentParser, Generic[_QueryT]):
    """
    Parses query params of the request.

    For example:

    .. code:: python

        >>> import pydantic
        >>> from django_modern_rest import Query, Controller
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class ProductQuery(pydantic.BaseModel):
        ...     category: str
        ...     reversed: bool

        >>> class ProductListController(
        ...     Query[ProductQuery],
        ...     Controller[PydanticSerializer],
        ... ):
        ...     ...

    Will parse a request like ``?category=cars&reversed=true``
    into ``ProductQuery`` model.

    You can access parsed query as ``self.parsed_query`` attribute.
    """

    parsed_query: _QueryT
    context_name: ClassVar[str] = 'parsed_query'

    @override
    @classmethod
    def provide_context_data(
        cls,
        blueprint: 'Blueprint[BaseSerializer]',
        model: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return request.GET


class Body(ComponentParser, Generic[_BodyT]):
    """
    Parses body of the request.

    For example:

    .. code:: python

        >>> import pydantic
        >>> from django_modern_rest import Body, Controller
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class UserCreateInput(pydantic.BaseModel):
        ...     email: str
        ...     age: int

        >>> class UserCreateController(
        ...     Body[UserCreateInput],
        ...     Controller[PydanticSerializer],
        ... ):
        ...     ...

    Will parse a body like ``{'email': 'user@mail.ru', 'age': 18}`` into
    ``UserCreateInput`` model.

    You can access parsed body as ``self.parsed_body`` attribute.
    """

    parsed_body: _BodyT
    context_name: ClassVar[str] = 'parsed_body'

    @override
    @classmethod
    def provide_context_data(
        cls,
        blueprint: 'Blueprint[BaseSerializer]',
        model: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        serializer = blueprint.serializer
        if request.content_type != serializer.content_type:
            raise RequestSerializationError(
                serializer.error_serialize(
                    'Cannot parse request body '
                    f'with content type {request.content_type!r}, '
                    f'expected {serializer.content_type!r}',
                ),
            )
        try:
            return serializer.deserialize(request.body)
        except DataParsingError as exc:
            raise RequestSerializationError(
                serializer.error_serialize(str(exc)),
            ) from exc


class Headers(ComponentParser, Generic[_HeadersT]):
    """
    Parses request headers.

    For example:

    .. code:: python

        >>> import pydantic
        >>> from django_modern_rest import Headers, Controller
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class AuthHeaders(pydantic.BaseModel):
        ...     token: str = pydantic.Field(alias='X-API-Token')

        >>> class UserCreateController(
        ...     Headers[AuthHeaders],
        ...     Controller[PydanticSerializer],
        ... ):
        ...     ...

    Will parse request headers like ``Token: secret`` into ``AuthHeaders``
    model.

    You can access parsed headers as ``self.parsed_headers`` attribute.
    """

    parsed_headers: _HeadersT
    context_name: ClassVar[str] = 'parsed_headers'

    @override
    @classmethod
    def provide_context_data(
        cls,
        blueprint: 'Blueprint[BaseSerializer]',
        model: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return request.headers


class Path(ComponentParser, Generic[_PathT]):
    """
    Parses the url part of the request.

    For example:

    .. code:: python

        >>> import pydantic
        >>> from django_modern_rest import Path, Controller
        >>> from django_modern_rest.routing import Router
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer
        >>> from django.urls import include, path

        >>> class UserPath(pydantic.BaseModel):
        ...     user_id: int

        >>> class UserUpdateController(
        ...     Path[UserPath],
        ...     Controller[PydanticSerializer],
        ... ):
        ...     ...

        >>> router = Router([
        ...     path(
        ...         'user/<int:user_id>',
        ...         UserUpdateController.as_view(),
        ...         name='users',
        ...     ),
        ... ])

        >>> urlpatterns = [
        ...     path(
        ...         'api/', include((router.urls, 'rest_app'), namespace='api')
        ...     ),
        ... ]

    Will parse a url path like ``/user_id/100``
    which will be translated into ``{'user_id': 100}``
    into ``UserPath`` model.

    If your controller class inherits from ``Path`` - then you can access
    parsed paths parameters as ``self.parsed_path`` attribute.

    It is way stricter than the original Django's routing system.
    For example, django allows to such cases:

    - ``user_id`` is defined as ``int`` in the ``path('user/<int:user_id>')``
    - ``user_id`` is defined as ``str`` in the view function:
      ``def get(self, request, user_id: str): ...``

    In ``django-modern-rest`` there's now a way to validate this in runtime.
    """

    parsed_path: _PathT
    context_name: ClassVar[str] = 'parsed_path'

    @override
    @classmethod
    def provide_context_data(
        cls,
        blueprint: 'Blueprint[BaseSerializer]',
        model: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if args:
            raise RequestSerializationError(
                f'Path {cls} with {model=} does not allow '
                f'unnamed path parameters {args=}',
            )
        return kwargs


class Cookies(ComponentParser, Generic[_CookiesT]):
    """
    Parses the cookies from :attr:`django.http.HttpRequest.COOKIES`.

    For example:

    .. code:: python

        >>> import pydantic
        >>> from django_modern_rest import Cookies, Controller
        >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

        >>> class UserSession(pydantic.BaseModel):
        ...     session_id: int

        >>> class UserUpdateController(
        ...     Cookies[UserSession],
        ...     Controller[PydanticSerializer],
        ... ):
        ...     ...


    Will parse a request header like ``Cookie: session_id=123``
    into a model ``UserSession``.

    You can access parsed cookies as ``self.parsed_cookies`` attribute.

    .. seealso::

        https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cookie

    """

    parsed_cookies: _CookiesT
    context_name: ClassVar[str] = 'parsed_cookies'

    @override
    @classmethod
    def provide_context_data(
        cls,
        blueprint: 'Blueprint[BaseSerializer]',
        model: Any,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return request.COOKIES
