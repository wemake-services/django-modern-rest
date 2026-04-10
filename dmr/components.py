import abc
from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Final,
    TypeAlias,
    TypeVar,
)

from django.utils.translation import gettext_lazy as _
from typing_extensions import override

from dmr.exceptions import (
    DataParsingError,
    EndpointMetadataError,
    RequestSerializationError,
    UnsolvableAnnotationsError,
)
from dmr.files import FileBody
from dmr.internal.django import (
    convert_multi_value_dict,
    extract_files_metadata,
    parse_headers,
)
from dmr.metadata import (
    ComponentParserSpec,
    EndpointMetadata,
    ResponseSpec,
    ResponseSpecProvider,
    get_annotated_metadata,
)
from dmr.negotiation import get_conditional_types
from dmr.openapi.objects import (
    MediaType,
    MediaTypeMetadata,
    Parameter,
    Reference,
    RequestBody,
)
from dmr.parsers import SupportsDjangoDefaultParsing, SupportsFileParsing
from dmr.types import TypeVarInference

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer

_UNNAMED_PATH_PARAMS_MSG: Final = _(
    'Path {cls} with field_model={field_model}'
    ' does not allow unnamed path parameters'
    ' args={args}',
)
_UNSUPPORTED_FILE_PARSER_MSG: Final = _(
    'Trying to parse files with {parser_name}'
    ' that does not support'
    ' SupportsFileParsing protocol',
)

_QueryT = TypeVar('_QueryT')
_BodyT = TypeVar('_BodyT')
_HeadersT = TypeVar('_HeadersT')
_PathT = TypeVar('_PathT')
_CookiesT = TypeVar('_CookiesT')
_FileMetadataT = TypeVar('_FileMetadataT')


class ComponentParserBuilder:
    """
    Find the component parser types in the MRO and find model types for them.

    Validates that component parsers can't have
    type vars as models at this point.
    """

    __slots__ = ('_controller_cls', '_func', '_type_annotations')

    type_var_inference_cls: ClassVar[type[TypeVarInference]] = TypeVarInference

    def __init__(
        self,
        func: Callable[..., Any],
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        """Initialize the builder."""
        self._func = func
        self._controller_cls = controller_cls

    def __call__(
        self,
        type_annotations: dict[str, Any],
    ) -> list[ComponentParserSpec]:
        """Run the building process, infer type vars if needed."""
        return self._resolve_type_vars(
            self._find_components(type_annotations),
        )

    def _find_components(  # noqa: WPS231
        self,
        type_annotations: dict[str, Any],
    ) -> list[ComponentParserSpec]:  # noqa: WPS231
        components: list[ComponentParserSpec] = []
        for context_name, component in type_annotations.items():
            if context_name == 'return':
                continue

            metadata = get_annotated_metadata(
                component,
                (),
                ComponentParser,  # type: ignore[type-abstract]
            )
            if metadata is None:
                continue

            if context_name != metadata.context_name:
                raise UnsolvableAnnotationsError(
                    f'Parameter name for {metadata} must always be '
                    f'{metadata.context_name} not {context_name!r} '
                    f'in {self._controller_cls!r}',
                )

            components.append((
                metadata,
                component.__origin__,
                component.__metadata__,
            ))

        return components

    def _resolve_type_vars(
        self,
        components: list[ComponentParserSpec],
    ) -> list[ComponentParserSpec]:
        return [self._resolve_component(component) for component in components]

    def _resolve_component(
        self,
        component_spec: ComponentParserSpec,
    ) -> ComponentParserSpec:
        if not isinstance(component_spec[1], TypeVar):
            # Component is not generic, just return whatever it has.
            return component_spec

        type_map = self.type_var_inference_cls(
            component_spec[1],
            self._controller_cls,
        )()
        return (
            component_spec[0],
            type_map[component_spec[1]],
            component_spec[2],
        )


class ComponentParser(ResponseSpecProvider):
    """Base abstract provider for request components."""

    __slots__ = ()

    # Public API:
    context_name: ClassVar[str]
    """
    All subtypes must provide a unique name that will be used to parse context.

    We use a single context for all parsing, this component
    will live under a dict field with this name.
    """

    @abc.abstractmethod
    def provide_context_data(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
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

    def conditional_types(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
    ) -> Mapping[str, Any]:
        """
        Provide conditional parsing types based on content type.

        Some components parser might define different input models
        based on the request's content type.

        This method must return a mapping of content_type to the model.
        If this component support this.
        """
        return {}

    def validate(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        metadata: EndpointMetadata,
    ) -> None:
        """
        Validates that the component is correctly defined.

        By default does nothing.
        Runs in import time.
        """

    @abc.abstractmethod
    def get_schema(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> list[Parameter | Reference] | RequestBody:
        """Generate OpenAPI spec for component."""
        raise NotImplementedError


class QueryComponent(ComponentParser):
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

        >>> class ProductListController(Controller[PydanticSerializer]):
        ...     def get(self, parsed_query: Query[ProductQuery]) -> str:
        ...         return parsed_query.category

    Will parse a request like ``?category=cars&reversed=true``
    into ``ProductQuery`` model.

    Parameter for ``Query`` component must be named ``parsed_query``.
    """

    __slots__ = ()
    context_name: ClassVar[str] = 'parsed_query'

    @override
    def provide_context_data(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        *,
        field_model: Any,
    ) -> dict[str, Any]:
        force_list: frozenset[str] = getattr(
            field_model,
            '__dmr_force_list__',
            frozenset(),
        )
        cast_null: frozenset[str] = getattr(
            field_model,
            '__dmr_cast_null__',
            frozenset(),
        )
        return convert_multi_value_dict(
            controller.request.GET,
            force_list=force_list,
            cast_null=cast_null,
        )

    @override
    def get_schema(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> list[Parameter | Reference] | RequestBody:
        return context.generators.parameter(
            model,
            model_meta,
            serializer,
            context,
            param_in='query',
        )


Query: TypeAlias = Annotated[_QueryT, QueryComponent()]
"""Annotated alias for parsing query parameters."""


class BodyComponent(ComponentParser):
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

        >>> class UserCreateController(Controller[PydanticSerializer]):
        ...     def post(self, parsed_body: Body[UserCreateInput]) -> str:
        ...         return parsed_body.email

    Will parse a body like ``{'email': 'user@example.org', 'age': 18}`` into
    ``UserCreateInput`` model.

    Parameter for ``Body`` component must be named ``parsed_body``.

    When working with parsers that support
    :class:`dmr.parsers.SupportsDjangoDefaultParsing` interface,
    you can specify ``__dmr_split_commas__`` attribute:
    it must contain a :class:`frozenset` of field aliases
    that will be split by ``','`` char.
    """

    __slots__ = ()
    context_name: ClassVar[str] = 'parsed_body'

    @override
    def provide_context_data(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        parser = endpoint.request_negotiator(controller.request)
        if isinstance(parser, SupportsDjangoDefaultParsing):
            # Special case, since this is the default content type
            # for Django's request body, it is already parsed.
            # No double work will be done:
            controller.serializer.deserialize(
                b'',  # it does not matter what to send here.
                parser=parser,
                request=controller.request,
                model=field_model,
            )
            # Django's native parsing is a mess:
            force_list: frozenset[str] = getattr(
                field_model,
                '__dmr_force_list__',
                frozenset(),
            )
            cast_null: frozenset[str] = getattr(
                field_model,
                '__dmr_cast_null__',
                frozenset(),
            )
            split_commas: frozenset[str] = getattr(
                field_model,
                '__dmr_split_commas__',
                frozenset(),
            )
            return convert_multi_value_dict(
                controller.request.POST,
                force_list=force_list,
                cast_null=cast_null,
                split_commas=split_commas,
            )

        try:
            return controller.serializer.deserialize(
                controller.request.body,
                parser=parser,
                request=controller.request,
                model=field_model,
            )
        except DataParsingError as exc:
            raise RequestSerializationError(str(exc)) from None

    @override
    def conditional_types(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
    ) -> Mapping[str, Any]:
        """
        Provide conditional parsing types based on content type.

        Body model can be conditional based on a content_type.
        If :data:`typing.Annotated` is passed together
        with :func:`dmr.negotiation.conditional_type`
        we treat the body as conditional. Otherwise, returns an empty dict.
        """
        return get_conditional_types(model, model_meta) or {}

    @override
    def get_schema(  # noqa: WPS210
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> list[Parameter | Reference] | RequestBody:
        schema = context.generators.schema(model, serializer)
        conditional_types = self.conditional_types(model, model_meta)
        conditional_schemas = {
            content_type: context.generators.schema(
                conditional_model,
                serializer,
            )
            for content_type, conditional_model in conditional_types.items()
        }
        media_types: dict[str, MediaType] = {}
        for parser in metadata.parsers.values():
            media_type_meta = (
                get_annotated_metadata(
                    conditional_types.get(parser.content_type, model),
                    model_meta,
                    MediaTypeMetadata,
                )
                or MediaTypeMetadata()
            )
            media_types[parser.content_type] = MediaType(
                schema=conditional_schemas.get(parser.content_type, schema),
                example=media_type_meta.example,
                examples=media_type_meta.examples,
                encoding=media_type_meta.encoding,
                item_encoding=media_type_meta.item_encoding,
                prefix_encoding=media_type_meta.prefix_encoding,
            )

        return RequestBody(
            content=media_types,
            required=True,
            description=context.registries.schema.maybe_resolve_reference(
                schema,
            ).description,
        )


Body: TypeAlias = Annotated[_BodyT, BodyComponent()]
"""Annotated alias for parsing requests bodies."""


class HeadersComponent(ComponentParser):
    """
    Parses request headers.

    For example:

    .. code:: python

        >>> import pydantic
        >>> from dmr import Headers, Controller
        >>> from dmr.plugins.pydantic import PydanticSerializer

        >>> class AuthHeaders(pydantic.BaseModel):
        ...     token: str = pydantic.Field(alias='X-API-Token')

        >>> class UserCreateController(Controller[PydanticSerializer]):
        ...     def get(self, parsed_headers: Headers[AuthHeaders]) -> str:
        ...         return parsed_headers.token

    Will parse request headers like ``Token: secret`` into ``AuthHeaders``
    model.

    Parameter for ``Headers`` component must be named ``parsed_headers``.
    """

    __slots__ = ()
    context_name: ClassVar[str] = 'parsed_headers'

    @override
    def provide_context_data(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        split_commas: frozenset[str] | None = getattr(
            field_model,
            '__dmr_split_commas__',
            None,
        )
        if not split_commas:
            return controller.request.headers
        return parse_headers(
            controller.request.headers,
            split_commas=split_commas,
        )

    @override
    def get_schema(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> list[Parameter | Reference] | RequestBody:
        return context.generators.parameter(
            model,
            model_meta,
            serializer,
            context,
            param_in='header',
        )


Headers: TypeAlias = Annotated[_HeadersT, HeadersComponent()]
"""Annotated alias for parsing header parameters."""


class PathComponent(ComponentParser):
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

        >>> class UserUpdateController(Controller[PydanticSerializer]):
        ...     def get(self, parsed_path: Path[UserPath]) -> int:
        ...         return parsed_path.user_id

        >>> router = Router(
        ...     'api/',
        ...     [
        ...         path(
        ...             'user/<int:user_id>',
        ...             UserUpdateController.as_view(),
        ...             name='users',
        ...         ),
        ...     ],
        ... )

        >>> urlpatterns = [
        ...     path(
        ...         router.prefix,
        ...         include((router.urls, 'rest_app'), namespace='api'),
        ...     ),
        ... ]

    Will parse a url path like ``/user_id/100``
    which will be translated into ``{'user_id': 100}``
    into ``UserPath`` model.

    Parameter for ``Path`` component must be named ``parsed_path``.

    It is way stricter than the original Django's routing system.
    For example, django allows to such cases:

    - ``user_id`` is defined as ``int`` in the ``path('user/<int:user_id>')``
    - ``user_id`` is defined as ``str`` in the view function:
      ``def get(self, request, user_id: str): ...``

    In ``django-modern-rest`` there's now a way to validate this in runtime.
    """

    __slots__ = ()
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
    def provide_context_data(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        if controller.args:
            raise RequestSerializationError(
                _UNNAMED_PATH_PARAMS_MSG.format(
                    cls=type(controller),
                    field_model=repr(field_model),
                    args=repr(controller.args),
                ),
            )
        return controller.kwargs

    @override
    def get_schema(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> list[Parameter | Reference] | RequestBody:
        return context.generators.parameter(
            model,
            model_meta,
            serializer,
            context,
            param_in='path',
        )


Path: TypeAlias = Annotated[_PathT, PathComponent()]
"""Annotated alias for parsing path parameters."""


class CookiesComponent(ComponentParser):
    """
    Parses the cookies from :attr:`django.http.HttpRequest.COOKIES`.

    For example:

    .. code:: python

        >>> import pydantic
        >>> from dmr import Cookies, Controller
        >>> from dmr.plugins.pydantic import PydanticSerializer

        >>> class UserSession(pydantic.BaseModel):
        ...     session_id: int

        >>> class UserUpdateController(Controller[PydanticSerializer]):
        ...     def get(self, parsed_cookies: Cookies[UserSession]) -> int:
        ...         return parsed_cookies.session_id

    Will parse a request header like ``Cookie: session_id=123``
    into a model ``UserSession``.

    Parameter for ``Cookies`` component must be named ``parsed_cookies``.

    .. seealso::

        https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cookie

    """

    __slots__ = ()
    context_name: ClassVar[str] = 'parsed_cookies'

    @override
    def provide_context_data(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Any:
        return controller.request.COOKIES

    @override
    def get_schema(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> list[Parameter | Reference] | RequestBody:
        return context.generators.parameter(
            model,
            model_meta,
            serializer,
            context,
            param_in='cookie',
        )


Cookies: TypeAlias = Annotated[_CookiesT, CookiesComponent()]
"""Annotated alias for parsing cookie parameters."""


class FileMetadataComponent(ComponentParser):
    """
    Parses files metadata from :attr:`django.http.HttpRequest.FILES`.

    Django handles files itself natively, we don't need to do anything
    in ``django-modern-rest``. Everything just works, including all
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

        >>> class ContractController(Controller[PydanticSerializer]):
        ...     parsers = (MultiPartParser(),)
        ...
        ...     def post(
        ...         self, parsed_file_metadata: FileMetadata[ContractPayload]
        ...     ) -> str:
        ...         return 'Valid files!'

    What attributes are available to be validated?
    See :class:`django.core.files.uploadedfile.UploadedFile`
    for the full list of metadata attributes.

    Parameter for ``FileMetadata`` component
    must be named ``parsed_file_metadata``.

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

    .. seealso::

        https://docs.djangoproject.com/en/stable/topics/http/file-uploads/

    """

    __slots__ = ('schema_metadata',)
    context_name: ClassVar[str] = 'parsed_file_metadata'

    def __init__(self, schema_metadata: type[FileBody] = FileBody) -> None:
        """Provide model type for a schema generation."""
        self.schema_metadata = schema_metadata

    @override
    def provide_context_data(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        *,
        field_model: Any,
    ) -> Mapping[str, Any]:
        parser = endpoint.request_negotiator(controller.request)
        if not isinstance(parser, SupportsFileParsing):
            raise RequestSerializationError(
                _UNSUPPORTED_FILE_PARSER_MSG.format(
                    parser_name=repr(type(parser).__name__),
                ),
            )

        # NOTE: double parsing does not happen.
        # Cases:
        # 1. `Body[]` exists: we set the parsing results on first request
        #    parsing and reuse it
        # 2. It is a single component: we reuse `request.FILES`
        #    when it is possible.
        controller.serializer.deserialize(
            b'',  # it does not matter what to send here.
            parser=parser,
            request=controller.request,
            model=field_model,
        )

        force_list: frozenset[str] = getattr(
            field_model,
            '__dmr_force_list__',
            frozenset(),
        )
        return extract_files_metadata(controller.request.FILES, force_list)

    @override
    def validate(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        metadata: EndpointMetadata,
    ) -> None:
        """
        Validates that the component is correctly defined.

        This component requires at least one
        :class:`dmr.parsers.SupportsFileParsing` instance
        to be present in parsers.

        Runs in import time.
        """
        if not any(
            isinstance(parser, SupportsFileParsing)
            for parser in metadata.parsers.values()
        ):
            hint = list(metadata.parsers.keys())
            raise EndpointMetadataError(
                f'Class {controller_cls!r} requires at least one parser '
                f'that can parse files, found: {hint}',
            )

    @override
    def conditional_types(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
    ) -> Mapping[str, Any]:
        """
        Provide conditional parsing types based on content type.

        Body model can be conditional based on a content_type.
        If :data:`typing.Annotated` is passed together
        with :func:`dmr.negotiation.conditional_type`
        we treat the body as conditional. Otherwise, returns an empty dict.
        """
        # TODO: test conditional file models and add `application/ocet-stream`
        # parser support to test it.
        return get_conditional_types(model, model_meta) or {}

    @override
    def get_schema(
        self,
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: EndpointMetadata,
        serializer: type['BaseSerializer'],
        context: 'OpenAPIContext',
    ) -> list[Parameter | Reference] | RequestBody:
        schema = context.generators.schema(
            model,
            serializer,
            skip_registration=True,
        )
        conditional_schemas = {
            content_type: context.generators.schema(
                conditional_model,
                serializer,
            )
            for content_type, conditional_model in self.conditional_types(
                model,
                model_meta,
            ).items()
        }
        return RequestBody(
            content={
                parser.content_type: self.schema_metadata.media_type(
                    conditional_schemas.get(parser.content_type, schema),
                    model,
                    model_meta,
                    parser,
                    context,
                )
                for parser in metadata.parsers.values()
            },
            required=True,
            description=context.registries.schema.maybe_resolve_reference(
                schema,
            ).description,
        )


FileMetadata: TypeAlias = Annotated[
    _FileMetadataT,
    FileMetadataComponent(),
]
"""Annotated alias for parsing file metadata."""
