import dataclasses
import uuid
from collections.abc import Mapping
from typing import (  # noqa: WPS235
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    TypeAlias,
    TypeVar,
    final,
)

from django.urls import converters
from typing_extensions import TypedDict

from dmr.internal.regex import parse_named_groups
from dmr.internal.types import EMPTY
from dmr.openapi.collector import InternalRouteMetadata
from dmr.openapi.objects import (
    MediaType,
    Parameter,
    Reference,
    RequestBody,
    Schema,
)

if TYPE_CHECKING:
    from dmr.components import ComponentParserSpec
    from dmr.controller import Controller
    from dmr.metadata import EndpointMetadata
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer


_RequestBody: TypeAlias = RequestBody | Reference | None
_RequestParameters: TypeAlias = list[Parameter | Reference] | None

_SLUG_REGEX: Final = converters.SlugConverter.regex

#: Path parameters are special: they are always required.
_PATH_LOCATION: Final = 'path'

# In json schema `pattern` is a search, but a url converter always matches
# the whole value, so we anchor the regex on both sides.
# It is also wrapped into a group, because anchors bind weaker than `|`:
# `^json|xml$` means "starts with `json`" or "ends with `xml`".
_SLUG_PATTERN: Final = f'^(?:{_SLUG_REGEX})$'


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ConverterSchema:
    """
    Prepared OpenAPI schema of a single Django path converter.

    Built-in converters use it to document themselves, and custom ones can
    provide their own instance through the ``__dmr_converter_schema__``
    attribute. Explicit values always override the generated ones.
    """

    model: Any = str
    pattern: str | None = None
    description: str | None = None


_ConvertersMapping: TypeAlias = Mapping[type[Any], ConverterSchema]


@dataclasses.dataclass(frozen=True, slots=True)
class ComponentParserGenerator:  # noqa: WPS214
    """Generator for OpenAPI ``Parameter`` objects."""

    _context: 'OpenAPIContext'

    # Class API:
    _converters: ClassVar[_ConvertersMapping] = {
        converters.IntConverter: ConverterSchema(model=int),
        converters.UUIDConverter: ConverterSchema(model=uuid.UUID),
        converters.SlugConverter: ConverterSchema(pattern=_SLUG_PATTERN),
        converters.PathConverter: ConverterSchema(
            description='Can contain slashes',
        ),
        # Any custom registered converter can have a `__dmr_converter_schema__`
        # attribute with either a model or a `ConverterSchema` instance.
    }

    def __call__(
        self,
        operation_id: str,
        route_metadata: InternalRouteMetadata,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> tuple[_RequestBody, _RequestParameters]:
        """
        Generate parameters from parsers.

        Components with default values are optional:
        their request bodies are not required
        and their parameters are not required as well.
        Except for path parameters, they are always required by OpenAPI.

        .. versionchanged:: 0.16.0
            Now accepts *controller_cls* parameter instead of *serializer*.
            Now accepts *route_metadata* parameter instead of *pattern*.
            Components with default values are now optional.

        """
        params_list: list[Parameter | Reference] = []
        request_body: RequestBody | None = None

        for spec in metadata.component_parsers:
            schema = self._call_component(spec, metadata, controller_cls)
            if isinstance(schema, RequestBody):
                request_body = self._merge_bodies(schema, request_body)
            else:
                params_list.extend(schema)

        pattern_param = self._parse_pattern(
            operation_id,
            route_metadata,
            params_list,
            metadata,
            controller_cls,
        )
        if pattern_param is not None:
            params_list.extend(pattern_param)

        return request_body, params_list or None

    def _call_component(
        self,
        spec: 'ComponentParserSpec',
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[Parameter | Reference] | RequestBody:
        schema = spec.parser.get_schema(
            spec.model,
            spec.model_meta,
            metadata=metadata,
            controller_cls=controller_cls,
            context=self._context,
        )
        if isinstance(schema, RequestBody):
            if spec.default is not EMPTY:
                schema.required = False
            return schema
        if isinstance(schema, list):  # pyright: ignore[reportUnnecessaryIsInstance]
            if spec.default is not EMPTY:
                self._mark_optional(schema)
            return schema
        raise TypeError(
            f'Returning {type(schema)!r} '
            'from ComponentParser.get_schema is not supported',
        )

    def _mark_optional(
        self,
        params_list: list[Parameter | Reference],
    ) -> None:
        for param_spec in params_list:
            # OpenAPI requires all path parameters to be required:
            if (
                isinstance(param_spec, Parameter)
                and param_spec.param_in != _PATH_LOCATION
            ):
                param_spec.required = None

    def _parse_pattern(
        self,
        operation_id: str,
        route_metadata: InternalRouteMetadata,
        parameter_specs: list[Parameter | Reference],
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[Parameter | Reference] | None:
        # TODO: support `parameter` references:
        if any(
            param_spec.param_in == _PATH_LOCATION
            for param_spec in parameter_specs
            if isinstance(param_spec, Parameter)
        ):
            # TODO: should we validate `Path` component on `Router` creation?
            # We already have some `Path` component, so move on.
            return None

        # `re_path()` and `RegexPattern`:
        if route_metadata.is_regex:
            return self._parse_regex(
                operation_id,
                route_metadata,
                metadata,
                controller_cls,
            )

        # `path()` and `RoutePattern`:
        return self._parse_converters(
            operation_id,
            route_metadata,
            metadata,
            controller_cls,
        )

    def _add_group_patterns(
        self,
        params_list: list[Parameter | Reference],
        regex_source: str,
    ) -> list[Parameter | Reference]:
        # In json schema `pattern` is a search, but a url group always
        # matches the whole value, so we anchor the sub-pattern:
        # `(?P<year>[0-9]{4})` becomes `^(?:[0-9]{4})$`.
        # It is also wrapped, because anchors bind weaker than `|`:
        # `^json|xml$` would mean "starts with `json`" or "ends with `xml`",
        # while `^(?:json|xml)$` means what `(?P<format>json|xml)` matches.
        named_groups = {
            group_name: f'^(?:{group_source})$'
            for group_name, group_source in parse_named_groups(
                regex_source,
            ).items()
        }
        for param_spec in params_list:
            # We've just built these parameters from a `TypedDict`
            # of plain `str` fields, one per named group,
            # so they all have inline schemas and none of them is a reference:
            assert isinstance(param_spec, Parameter)  # noqa: S101
            assert isinstance(param_spec.schema, Schema)  # noqa: S101
            param_spec.schema.pattern = named_groups.get(param_spec.name)
        return params_list

    def _parse_converters(
        self,
        operation_id: str,
        route_metadata: InternalRouteMetadata,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[Parameter | Reference] | None:
        prepared = {
            converter_name: _converter_schema(converter, self._converters)
            for converter_name, converter in route_metadata.converters().items()
        }
        if not prepared:
            return None
        return self._add_converter_schemas(
            self._context.generators.parameter(
                TypedDict(  # type: ignore[operator]
                    f'{operation_id}_Path',
                    _converter_models(prepared),
                ),
                (),
                metadata,
                controller_cls,
                param_in=_PATH_LOCATION,
            ),
            prepared,
        )

    def _parse_regex(
        self,
        operation_id: str,
        route_metadata: InternalRouteMetadata,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[Parameter | Reference] | None:
        assert route_metadata.is_regex  # noqa: S101
        regex = route_metadata.regex()
        schema = dict.fromkeys(regex.groupindex, str)
        return (
            self._add_group_patterns(
                self._context.generators.parameter(
                    TypedDict(f'{operation_id}_RePath', schema),  # type: ignore[operator]
                    (),
                    metadata,
                    controller_cls,
                    param_in=_PATH_LOCATION,
                ),
                regex.pattern,
            )
            or None
        )

    def _add_converter_schemas(
        self,
        params_list: list[Parameter | Reference],
        prepared: Mapping[str, ConverterSchema],
    ) -> list[Parameter | Reference]:
        for param_spec in params_list:
            # We've just built these parameters, one per converter:
            assert isinstance(param_spec, Parameter)  # noqa: S101
            if not isinstance(param_spec.schema, Schema):
                # A custom converter can declare a model, and such a model
                # is generated as a component reference. There is no inline
                # schema to override, so we keep the reference as it is:
                continue
            converter_schema = prepared[param_spec.name]
            param_spec.schema.pattern = (
                converter_schema.pattern or param_spec.schema.pattern
            )
            param_spec.schema.description = (
                converter_schema.description or param_spec.schema.description
            )
        return params_list

    def _merge_bodies(
        self,
        new_schema: RequestBody,
        schema: RequestBody | None,
    ) -> RequestBody:
        if schema is None:
            return new_schema
        new_content = self._merge_contents(new_schema, schema)

        return RequestBody(
            content=new_content,
            description=(
                (
                    (schema.description or '')
                    + ' '
                    + (new_schema.description or '')
                ).strip()
                or None
            ),
            required=schema.required or new_schema.required,
        )

    def _merge_contents(
        self,
        new_schema: RequestBody,
        schema: RequestBody,
    ) -> dict[str, MediaType | Reference]:
        # A required body component has to parse every request, so it rules
        # out the content types it does not support. An optional one does
        # not: a request it cannot parse is simply a request without it.
        merged: dict[str, MediaType | Reference] = {}
        # Sorted by content type, custom components can return any order:
        media_names = new_schema.content.keys() | schema.content.keys()
        for media_name in sorted(media_names):
            media_type = _merge_media_types(
                schema.content.get(media_name),
                new_schema.content.get(media_name),
                # A content type only one of them supports survives
                # when the other one is optional:
                keep_lonely_existing=not new_schema.required,
                keep_lonely_new=not schema.required,
            )
            if media_type is not None:
                merged[media_name] = media_type
        return merged


_MergedT = TypeVar('_MergedT')


def _merge_optional(
    existing: dict[str, _MergedT] | None,
    to_merge: dict[str, _MergedT] | None,
) -> dict[str, _MergedT] | None:
    """Merge two optional mappings, ``None`` when nothing is left."""
    return {**(existing or {}), **(to_merge or {})} or None


def _merge_media_types(
    existing: 'MediaType | Reference | None',
    to_merge: 'MediaType | Reference | None',
    *,
    keep_lonely_existing: bool,
    keep_lonely_new: bool,
) -> 'MediaType | Reference | None':
    """Merge what two body components say about one content type."""
    if existing is None:
        return to_merge if keep_lonely_new else None
    if to_merge is None:
        return existing if keep_lonely_existing else None

    # We've just built these bodies from component parsers,
    # so all of them have inline media types, never references.
    # They also always describe themselves with `schema`,
    # `item_schema` is only used for streaming responses:
    assert isinstance(existing, MediaType)  # noqa: S101
    assert isinstance(to_merge, MediaType)  # noqa: S101
    assert existing.schema is not None  # noqa: S101
    assert to_merge.schema is not None  # noqa: S101
    return dataclasses.replace(
        to_merge,
        # Declaration order, the existing body came first:
        schema=Schema(all_of=[existing.schema, to_merge.schema]),
        # Both are keyed by property name and describe different parts
        # of the same body, so neither of them may be lost:
        encoding=_merge_optional(existing.encoding, to_merge.encoding),
        examples=_merge_optional(existing.examples, to_merge.examples),
    )


def _converter_models(
    prepared: Mapping[str, ConverterSchema],
) -> dict[str, Any]:
    return {
        converter_name: converter_schema.model
        for converter_name, converter_schema in prepared.items()
    }


def _converter_schema(
    converter: Any,
    known_converters: Mapping[type[Any], ConverterSchema],
) -> ConverterSchema:
    known = known_converters.get(
        type(converter),  # pyright: ignore[reportUnknownArgumentType]
    )
    if known is not None:
        return known
    provided = getattr(converter, '__dmr_converter_schema__', None)
    if isinstance(provided, ConverterSchema):
        return provided
    return ConverterSchema(model=provided or str)
