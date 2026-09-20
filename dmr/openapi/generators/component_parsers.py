import dataclasses
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, ClassVar, Final, TypeAlias, final

from django.urls import URLPattern, converters
from typing_extensions import TypedDict

from dmr.internal.regex import parse_named_groups
from dmr.openapi.objects import (
    MediaType,
    Parameter,
    Reference,
    RequestBody,
    Schema,
)

if TYPE_CHECKING:
    from dmr.components import ComponentParser
    from dmr.metadata import EndpointMetadata
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer


_RequestBody: TypeAlias = RequestBody | Reference | None
_RequestParameters: TypeAlias = list[Parameter | Reference] | None

_SLUG_REGEX: Final = converters.SlugConverter.regex

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
        pattern: URLPattern,
        metadata: 'EndpointMetadata',
        serializer: type['BaseSerializer'],
    ) -> tuple[_RequestBody, _RequestParameters]:
        """Generate parameters from parsers."""
        params_list: list[Parameter | Reference] = []
        request_body: RequestBody | None = None

        for component in metadata.component_parsers:
            schema = self._call_component(
                *component,
                metadata,
                serializer,
            )

            if isinstance(schema, RequestBody):
                request_body = self._merge_bodies(schema, request_body)
            elif isinstance(schema, list):  # pyright: ignore[reportUnnecessaryIsInstance]
                params_list.extend(schema)
            else:
                raise TypeError(
                    f'Returning {type(schema)!r} '
                    'from ComponentParser.get_schema is not supported',
                )

        pattern_param = self._parse_pattern(
            operation_id,
            pattern,
            params_list,
            serializer,
        )
        if pattern_param is not None:
            params_list.extend(pattern_param)

        return request_body, params_list or None

    def _call_component(
        self,
        parser: 'ComponentParser',
        model: Any,
        model_meta: tuple[Any, ...],
        metadata: 'EndpointMetadata',
        serializer: type['BaseSerializer'],
    ) -> list[Parameter | Reference] | RequestBody:
        return parser.get_schema(
            model,
            model_meta,
            serializer=serializer,
            metadata=metadata,
            context=self._context,
        )

    def _parse_pattern(
        self,
        operation_id: str,
        pattern: URLPattern,
        parameter_specs: list[Parameter | Reference],
        serializer: type['BaseSerializer'],
    ) -> list[Parameter | Reference] | None:
        # TODO: support `parameter` references:
        if any(
            param_spec.param_in == 'path'
            for param_spec in parameter_specs
            if isinstance(param_spec, Parameter)
        ):
            # We already have some `Path` component, so move on.
            return None

        # `path()` and `RoutePattern`:
        converter_params = self._parse_converters(
            operation_id,
            pattern,
            serializer,
        )
        if converter_params is not None:
            return converter_params

        # `re_path()` and `RegexPattern`:
        regex = pattern.pattern.regex
        schema = dict.fromkeys(
            regex.groupindex,
            str,
        )
        if schema:
            return self._add_group_patterns(
                self._context.generators.parameter(
                    TypedDict(f'{operation_id}_RePath', schema),  # type: ignore[operator]
                    (),
                    serializer,
                    self._context,
                    param_in='path',
                ),
                regex.pattern,
            )
        return None

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
        pattern: URLPattern,
        serializer: type['BaseSerializer'],
    ) -> list[Parameter | Reference] | None:
        prepared = {
            converter_name: _converter_schema(converter, self._converters)
            for converter_name, converter in pattern.pattern.converters.items()
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
                serializer,
                self._context,
                param_in='path',
            ),
            prepared,
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
        new_content: dict[str, MediaType | Reference] = {}
        # Sorted by content type, custom components can return any order:
        for media_name, media_type in sorted(new_schema.content.items()):
            # We've just built these bodies from component parsers,
            # so all of them have inline media types, never references:
            assert isinstance(media_type, MediaType)  # noqa: S101
            media_items: list[Reference | Schema] = []
            if media_type.schema:  # pragma: no cover:
                media_items.append(media_type.schema)
            existing_content = schema.content.get(media_name)
            assert not isinstance(existing_content, Reference)  # noqa: S101
            # TODO: remove pragma after implementing conditional types
            # for `FileMetadata[]` component
            if existing_content and existing_content.schema:  # pragma: no cover
                media_items.append(existing_content.schema)
            new_content[media_name] = dataclasses.replace(
                media_type,
                schema=Schema(all_of=media_items),
            )
        return new_content


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
