import dataclasses
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias

from django.urls import URLPattern, converters
from typing_extensions import TypedDict

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


@dataclasses.dataclass(frozen=True, slots=True)
class _ConverterSchema:
    """Prepared OpenAPI schema of a single Django path converter."""

    model: Any = str
    pattern: str | None = None
    description: str | None = None


_ConvertersMapping: TypeAlias = Mapping[type[Any], _ConverterSchema]


def _anchored(regex: str) -> str:
    """Anchor a regex on both sides with a non-capturing group.

    A plain ``^...$`` would only anchor one side of an alternation,
    like ``^a|b$``.
    """
    return f'^(?:{regex})$'


def _converter_models(
    prepared: Mapping[str, _ConverterSchema],
) -> dict[str, Any]:
    """Build the ``TypedDict`` fields for the prepared converters."""
    return {
        converter_name: converter_schema.model
        for converter_name, converter_schema in prepared.items()
    }


def _with_converter_schema(
    param_spec: Parameter | Reference,
    prepared: Mapping[str, _ConverterSchema],
) -> Parameter | Reference:
    """Add the converter specific info to a generated parameter."""
    if not isinstance(param_spec, Parameter):
        return param_spec
    converter_schema = prepared.get(param_spec.name)
    if converter_schema is None or not isinstance(param_spec.schema, Schema):
        return param_spec
    if converter_schema.pattern is not None:
        param_spec.schema.pattern = converter_schema.pattern
    if converter_schema.description is not None:
        param_spec.schema.description = converter_schema.description
    return param_spec


@dataclasses.dataclass(frozen=True, slots=True)
class ComponentParserGenerator:
    """Generator for OpenAPI ``Parameter`` objects."""

    _context: 'OpenAPIContext'

    # Class API:
    _converters: ClassVar[_ConvertersMapping] = {
        converters.IntConverter: _ConverterSchema(model=int),
        converters.UUIDConverter: _ConverterSchema(model=uuid.UUID),
        converters.SlugConverter: _ConverterSchema(
            pattern=_anchored(converters.SlugConverter.regex),
        ),
        converters.PathConverter: _ConverterSchema(
            description='Can contain slashes',
        ),
        # Any custom registered converter can have `__dmr_converter_schema__`
        # attribute to resolve our schema.
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

        params_list: list[Parameter | Reference] = []

        # `path()` and `RoutePattern`:
        converter_params = self._parse_converters(
            operation_id,
            pattern,
            serializer,
        )
        if converter_params is not None:
            params_list.extend(converter_params)
            return params_list

        # `re_path()` and `RegexPattern`:
        regex = pattern.pattern.regex
        schema = dict.fromkeys(
            regex.groupindex,
            str,
        )
        if schema:
            params_list.extend(
                self._context.generators.parameter(
                    TypedDict(f'{operation_id}_RePath', schema),  # type: ignore[operator]
                    (),
                    serializer,
                    self._context,
                    param_in='path',
                ),
            )
        return params_list or None

    def _parse_converters(
        self,
        operation_id: str,
        pattern: URLPattern,
        serializer: type['BaseSerializer'],
    ) -> list[Parameter | Reference] | None:
        """Parse `path()` and `RoutePattern` converters."""
        prepared = {
            converter_name: self._converter_schema(converter)
            for converter_name, converter in pattern.pattern.converters.items()
        }
        if not prepared:
            return None
        return [
            _with_converter_schema(param_spec, prepared)
            for param_spec in self._context.generators.parameter(
                TypedDict(  # type: ignore[operator]
                    f'{operation_id}_Path',
                    _converter_models(prepared),
                ),
                (),
                serializer,
                self._context,
                param_in='path',
            )
        ]

    def _converter_schema(self, converter: Any) -> _ConverterSchema:
        """Resolve the prepared schema of a single path converter."""
        known = self._converters.get(
            type(converter),  # pyright: ignore[reportUnknownArgumentType]
        )
        if known is not None:
            return known
        return _ConverterSchema(
            model=getattr(converter, '__dmr_converter_schema__', str),
        )

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
                (schema.description or '')
                + ' '
                + (new_schema.description or '')
            ).strip(),
            required=schema.required or new_schema.required,
        )

    def _merge_contents(
        self,
        new_schema: RequestBody,
        schema: RequestBody,
    ) -> dict[str, 'MediaType']:
        new_content: dict[str, MediaType] = {}
        for media_name, media_type in new_schema.content.items():
            media_items: list[Reference | Schema] = []
            if media_type.schema:  # pragma: no cover:
                media_items.append(media_type.schema)
            existing_content = schema.content.get(media_name)
            # TODO: remove pragma after implementing conditional types
            # for `FileMetadata[]` component
            if existing_content and existing_content.schema:  # pragma: no cover
                media_items.append(existing_content.schema)
            new_content[media_name] = dataclasses.replace(
                media_type,
                schema=Schema(all_of=media_items),
            )
        return new_content
