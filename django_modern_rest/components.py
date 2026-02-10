import abc
from collections.abc import Mapping
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    TypeAlias,
    TypeVar,
    get_args,
)

from typing_extensions import override

from django_modern_rest.exceptions import (
    DataParsingError,
    RequestSerializationError,
    UnsolvableAnnotationsError,
)
from django_modern_rest.metadata import (
    EndpointMetadata,
    ResponseSpec,
    ResponseSpecProvider,
)
from django_modern_rest.negotiation import get_conditional_types
from django_modern_rest.types import (
    TypeVarInference,
    infer_bases,
    is_safe_subclass,
)

if TYPE_CHECKING:
    from django_modern_rest.controller import Blueprint, Controller
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.serializer import BaseSerializer

_QueryT = TypeVar('_QueryT')
_BodyT = TypeVar('_BodyT')
_HeadersT = TypeVar('_HeadersT')
_PathT = TypeVar('_PathT')
_CookiesT = TypeVar('_CookiesT')


ComponentParserSpec: TypeAlias = tuple[
    type['ComponentParser'],
    tuple[Any, ...],
]


class ComponentParserBuilder:
    """
    Find the component parser types in the MRO and find model types for them.

    Validates that component parsers can't have
    type vars as models at this point.
    """

    __slots__ = ('_blueprint_cls', '_ignore_cls')

    type_var_inference_cls: ClassVar[type[TypeVarInference]] = TypeVarInference

    def __init__(
        self,
        blueprint_cls: type['Blueprint[BaseSerializer]'],
        ignore_cls: type['Blueprint[BaseSerializer]'],
    ) -> None:
        """Initialize the builder."""
        self._blueprint_cls = blueprint_cls
        self._ignore_cls = ignore_cls

    def __call__(self) -> list[ComponentParserSpec]:
        """Run the building process, infer type vars if needed."""
        self._validate_args(self._find_components(use_origin=False))
        components = self._find_components()
        return self._resolve_type_vars(components)

    def _find_components(
        self,
        *,
        use_origin: bool = True,
    ) -> list[type['ComponentParser']]:
        return [
            orig
            for base in self._blueprint_cls.__mro__
            for orig in infer_bases(
                base,
                ComponentParser,
                use_origin=use_origin,
            )
            # When type is a subclass of `Blueprint`, it means that
            # a component parser type was already mixed in.
            if not is_safe_subclass(orig, self._ignore_cls)
        ]

    def _validate_args(self, components: list[type['ComponentParser']]) -> None:
        for component_cls in components:
            if component_cls is ComponentParser:
                continue

            if not get_args(component_cls):
                raise UnsolvableAnnotationsError(
                    f'Component {component_cls!r} in {self._blueprint_cls!r} '
                    'must have at least 1 type argument, given 0',
                )

    def _resolve_type_vars(
        self,
        components: list[type['ComponentParser']],
    ) -> list[ComponentParserSpec]:
        return [self._resolve_component(component) for component in components]

    def _resolve_component(
        self,
        component: type['ComponentParser'],
    ) -> ComponentParserSpec:
        type_params = getattr(component, '__parameters__', None)
        if not type_params:
            # Component is not generic, just return whatever it has.
            return (component, get_args(component))

        type_map = self.type_var_inference_cls(component, self._blueprint_cls)()
        return (
            component,
            tuple(type_map[type_param] for type_param in type_params),
        )


class ComponentParser(ResponseSpecProvider):
    """Base abstract provider for request components."""

    # Public API:
    context_name: ClassVar[str]
    """
    All subtypes must provide a unique name that will be used to parse context.

    We use a single context for all parsing, this component
    will live under a dict field with this name.
    """

    @classmethod
    @abc.abstractmethod
    def provide_context_data(
        cls,
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        """
        Return unstructured raw value for serializer.from_python().

        Implement body JSON decoding / content-type checks here if needed.
        """
        raise NotImplementedError

    @override
    @classmethod
    def provide_response_specs(
        cls,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """
        Return a list of extra responses that this component produces.

        For example, when parsing something, we always have an option
        to fail a parsing, if some request does not fit our model.
        """
        return cls._add_new_response(
            ResponseSpec(
                controller_cls.error_model,
                status_code=RequestSerializationError.status_code,
                description='Raised when request components cannot be parsed',
            ),
            existing_responses,
        )

    @classmethod
    def conditional_types(cls, model: Any) -> Mapping[str, Any]:
        """
        Provide conditional parsing types based on content type.

        Some components parser might define different input models
        based on the request's content type.

        This method must return a mapping of content_type to the model.
        If this component support this.
        """
        return {}


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
        ... ): ...

    Will parse a request like ``?category=cars&reversed=true``
    into ``ProductQuery`` model.

    You can access parsed query as ``self.parsed_query`` attribute.

    .. note::

        When working with ``msgspec`` as your serializer,
        be careful, because
        :class:`django.http.QueryDict` always returns a list
        for each key. And ``msgspec`` won't automatically convert
        a single item list to a regular value.

        Use
        ``Annotated[list[YourType], msgspec.Meta(min_length=1, max_length=1)]``
        instead of regular values.

    """

    parsed_query: _QueryT
    context_name: ClassVar[str] = 'parsed_query'

    @override
    @classmethod
    def provide_context_data(
        cls,
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        return blueprint.request.GET


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
        ... ): ...

    Will parse a body like ``{'email': 'user@example.org', 'age': 18}`` into
    ``UserCreateInput`` model.

    You can access parsed body as ``self.parsed_body`` attribute.
    """

    parsed_body: _BodyT
    context_name: ClassVar[str] = 'parsed_body'

    @override
    @classmethod
    def provide_context_data(
        cls,
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        parser_cls = endpoint.request_negotiator(blueprint.request)

        try:
            return blueprint.serializer.deserialize(
                blueprint.request.body,
                parser_cls=parser_cls,
            )
        except DataParsingError as exc:
            raise RequestSerializationError(str(exc)) from None

    @override
    @classmethod
    def conditional_types(cls, model: Any) -> Mapping[str, Any]:
        """
        Provide conditional parsing types based on content type.

        Body model can be conditional based on a content_type.

        This method must return a mapping of content_type to the model.
        If this component support this.
        """
        return get_conditional_types(model) or {}


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
        ... ): ...

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
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        return blueprint.request.headers


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
        ... ): ...

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
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        if blueprint.args:
            raise RequestSerializationError(
                f'Path {cls} with {field_model=} does not allow '
                f'unnamed path parameters {blueprint.args=}',
            )
        return blueprint.kwargs


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
        ... ): ...


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
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        return blueprint.request.COOKIES
