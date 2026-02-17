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

from dmr.exceptions import (
    DataParsingError,
    EndpointMetadataError,
    RequestSerializationError,
    UnsolvableAnnotationsError,
)
from dmr.internal.django import (
    convert_multi_value_dict,
    exctract_files_metadata,
)
from dmr.metadata import (
    EndpointMetadata,
    ResponseSpec,
    ResponseSpecProvider,
)
from dmr.negotiation import get_conditional_types
from dmr.parsers import SupportsDjangoDefaultParsing, SupportsFileParsing
from dmr.types import TypeVarInference, infer_bases, is_safe_subclass

if TYPE_CHECKING:
    from dmr.controller import Blueprint, Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer

_QueryT = TypeVar('_QueryT')
_BodyT = TypeVar('_BodyT')
_HeadersT = TypeVar('_HeadersT')
_PathT = TypeVar('_PathT')
_CookiesT = TypeVar('_CookiesT')
_FileMetadataT = TypeVar('_FileMetadataT')


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
    ) -> Any | tuple[Any, ...]:
        """
        Return unstructured raw values for ``serializer.from_python()``.

        It must return the same number of elements that has type vars.
        Basically, each type var is a model.
        Each element in a tuple is the corresponding data for that model.

        When this method returns not a tuple and there's only one type variable,
        it also works.
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

    @classmethod
    def validate(cls, metadata: EndpointMetadata) -> None:
        """
        Validates that the component is correctly defined.

        By default does nothing.
        Runs in import time.
        """


class Query(ComponentParser, Generic[_QueryT]):
    """
    Parses query params of the request.

    For example:

    .. code:: python

        >>> import pydantic
        >>> from dmr import Query, Controller
        >>> from dmr.plugins.pydantic import PydanticSerializer

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

    Internally query is represented
    as :class:`django.utils.datastructures.MultiValueDict` in Django.
    It supports several values for a single key.

    Users can customize how they want their values:
    as single values or as lists of values.
    To do so, use ``__dmr_force_list__`` optional attribute.
    Set it to :class:`frozenset` of values that need to be lists.
    All other values will be regular single values:

    .. code:: python

        >>> class SearchQuery(pydantic.BaseModel):
        ...     __dmr_force_list__: ClassVar[frozenset[str]] = frozenset((
        ...         'query',
        ...     ))
        ...
        ...     query: list[str]
        ...     reversed: bool

    This will parse a query like ``?query=text&query=match&reversed=1``
    into the provided model.

    We don't inference this value in any way, it is up to users to set.
    Inspecting annotations is hard and produce a lot of errors.
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
    ) -> dict[str, Any]:
        force_list: frozenset[str] = getattr(
            field_model,
            '__dmr_force_list__',
            frozenset(),
        )
        return convert_multi_value_dict(blueprint.request.GET, force_list)


class Body(ComponentParser, Generic[_BodyT]):
    """
    Parses body of the request.

    For example:

    .. code:: python

        >>> import pydantic
        >>> from dmr import Body, Controller
        >>> from dmr.plugins.pydantic import PydanticSerializer

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
    django_default_content_types: ClassVar[frozenset[str]] = frozenset((
        'multipart/form-data',
        'application/x-www-form-urlencoded',
    ))

    @override
    @classmethod
    def provide_context_data(
        cls,
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        parser = endpoint.request_negotiator(blueprint.request)
        if isinstance(parser, SupportsDjangoDefaultParsing):
            # Special case, since this is the default content type
            # for Django's request body, it is already parsed.
            # No double work will be done:
            blueprint.serializer.deserialize(
                b'',  # it does not matter what to send here.
                parser=parser,
                request=blueprint.request,
            )
            return blueprint.request.POST

        try:
            return blueprint.serializer.deserialize(
                blueprint.request.body,
                parser=parser,
                request=blueprint.request,
            )
        except DataParsingError as exc:
            raise RequestSerializationError(str(exc)) from None

    @override
    @classmethod
    def conditional_types(cls, model: Any) -> Mapping[str, Any]:
        """
        Provide conditional parsing types based on content type.

        Body model can be conditional based on a content_type.
        If :data:`typing.Annotated` is passed together
        with :func:`dmr.negotiation.conditional_type`
        we treat the body as conditional. Otherwise, returns an empty dict.
        """
        return get_conditional_types(model) or {}


class Headers(ComponentParser, Generic[_HeadersT]):
    """
    Parses request headers.

    For example:

    .. code:: python

        >>> import pydantic
        >>> from dmr import Headers, Controller
        >>> from dmr.plugins.pydantic import PydanticSerializer

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
        >>> from dmr import Path, Controller
        >>> from dmr.routing import Router
        >>> from dmr.plugins.pydantic import PydanticSerializer
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
    def provide_response_specs(
        cls,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """
        Return a list of extra responses that this component produces.

        Path component implies that we are looking for something.
        So, it is natural to have 404 in the specification.
        """
        return [
            *super().provide_response_specs(
                metadata,
                controller_cls,
                existing_responses,
            ),
            *cls._add_new_response(
                ResponseSpec(
                    controller_cls.error_model,
                    status_code=HTTPStatus.NOT_FOUND,
                    description='Raised when path parameters do not match',
                ),
                existing_responses,
            ),
        ]

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
        >>> from dmr import Cookies, Controller
        >>> from dmr.plugins.pydantic import PydanticSerializer

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


class FileMetadata(ComponentParser, Generic[_FileMetadataT]):
    """
    Parses files metadata from :attr:`django.http.HttpRequest.FILES`.

    Django handles files itself natively, we don't need to do anything
    in ``django_modern_rest``. Everything just works, including all
    Django's advanced file features like customizing the storage backends.

    But, we need a way to represent and validate the metadata.

    This class is designed to do just that: validate files' metadata.

    .. code:: python

        >>> from typing import Literal
        >>> import pydantic
        >>> from dmr import Controller, FileMetadata
        >>> from dmr.plugins.pydantic import PydanticSerializer
        >>> from dmr.parsers import MultiPartParser

        >>> class TextFile(pydantic.BaseModel):
        ...     # Will validate that all files are text files
        ...     # and are less than 1000 bytes in size:
        ...     name: str
        ...     content_type: Literal['text/plain']
        ...     size: int = pydantic.Field(lt=1000)

        >>> class ContractPayload(pydantic.BaseModel):
        ...     receipt: TextFile
        ...     contract: TextFile

        >>> class ContractController(
        ...     FileMetadata[ContractPayload],
        ...     Controller[PydanticSerializer],
        ... ):
        ...     parsers = (MultiPartParser(),)
        ...
        ...     def post(self) -> str:
        ...         return 'Valid files!'

    What attributes are available to be validated?
    See :class:`django.core.files.uploadedfile.UploadedFile`
    for the full list of metadata attributes.

    Users can customize how they want their file metadata values:
    as single values or as lists of values.
    To do so, use ``__dmr_force_list__`` optional attribute.
    Set it to :class:`frozenset` of file keys that need to be lists.
    All other values will be regular single values:

    .. code:: python

        >>> class ContractPayload(pydantic.BaseModel):
        ...     __dmr_force_list__: ClassVar[frozenset[str]] = frozenset((
        ...         'receipts',
        ...     ))
        ...
        ...     receipts: list[TextFile]
        ...     contract: TextFile

    This will parse a ``multipart/form-data`` request with potentially multiple
    receipts and a single contract files.

    You can access parsed files' metadata
    as ``self.parsed_file_metadata`` attribute.

    .. seealso::

        https://docs.djangoproject.com/en/6.0/topics/http/file-uploads/

    """

    parsed_file_metadata: _FileMetadataT
    context_name: ClassVar[str] = 'parsed_file_metadata'

    @override
    @classmethod
    def provide_context_data(
        cls,
        endpoint: 'Endpoint',
        blueprint: 'Blueprint[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Mapping[str, Any]:
        parser = endpoint.request_negotiator(blueprint.request)
        if not isinstance(parser, SupportsFileParsing):
            raise RequestSerializationError(
                f'Trying to parse files with {type(parser).__name__!r} '
                'that does not support SupportsFileParsing protocol',
            )

        # NOTE: double parsing does not happen.
        # Cases:
        # 1. `Body[]` exists: we set the parsing results on first request
        #    parsing and reuse it
        # 2. It is a single component: we reuse `request.FILES`
        #    when it is possible.
        blueprint.serializer.deserialize(
            b'',  # it does not matter what to send here.
            parser=parser,
            request=blueprint.request,
        )

        force_list: frozenset[str] = getattr(
            field_model,
            '__dmr_force_list__',
            frozenset(),
        )
        return exctract_files_metadata(blueprint.request.FILES, force_list)

    @override
    @classmethod
    def validate(cls, metadata: EndpointMetadata) -> None:
        """
        Validates that the component is correctly defined.

        This component requires at least one
        :class:`dmr.parsers.SupportsFileParser` instance
        to be present in parsers.

        Runs in import time.
        """
        if not any(
            isinstance(parser, SupportsFileParsing)
            for parser in metadata.parsers.values()
        ):
            hint = list(metadata.parsers.keys())
            raise EndpointMetadataError(
                f'Class {cls!r} requires at least one parser '
                f'that can parse files, found: {hint}',
            )
