from typing import Any, cast, final, get_origin

from typing_extensions import is_typeddict, override

try:
    import pydantic
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pydantic` is not installed, '
        "consider using `pip install 'django-modern-rest[pydantic]'`",
    )
    raise

from django_modern_rest.components import Body
from django_modern_rest.metadata import ComponentParserSpec
from django_modern_rest.openapi.extractors.base import BaseExtractor
from django_modern_rest.openapi.objects import (
    MediaType,
    Reference,
    RequestBody,
    Schema,
)


@final
class PydanticExtractor(BaseExtractor):
    """OpenAPI schema extractor for Pydantic models."""

    @override
    def supports_type(self, type_: Any) -> bool:
        """Check if this extractor can handle the given type."""
        # TODO: Too dirty. Need refactor
        if isinstance(type_, type) and issubclass(type_, pydantic.BaseModel):
            return True

        if is_typeddict(type_):  # pyright: ignore[reportUnknownArgumentType]
            return True

        try:
            pydantic.TypeAdapter(cast(Any, type_))
        except Exception:
            return False
        else:
            return True

    @override
    def extract_request_body(
        self,
        component_specs: list[ComponentParserSpec],
    ) -> RequestBody | None:
        """Extract RequestBody from Body component."""
        for component_cls, type_args in component_specs:
            origin = get_origin(component_cls) or component_cls
            if issubclass(origin, Body):
                body_type = type_args[0]
                return RequestBody(
                    content={
                        'application/json': self._extract_media_type(body_type),
                    },
                    required=True,
                )
        return None

    @override
    def extract_schema(self, type_: Any) -> Schema | Reference:
        """Extract OpenAPI Schema from pydantic type."""
        json_schema = pydantic.TypeAdapter(type_).json_schema(
            mode='serialization',
            ref_template='#/components/schemas/{model}',
        )

        # Extract and collect $defs if they exist
        defs = json_schema.pop('$defs', None)
        if defs and self.context:
            for def_name, def_schema in defs.items():
                self.context.collect_schema(
                    def_name,
                    self._convert_json_schema(def_schema),
                )

        # TODO: Maybe extract to method?
        # Get the title from the schema (model name)
        title = json_schema.get('title')
        if title and self.context:
            self.context.collect_schema(
                title,
                self._convert_json_schema(json_schema),
            )
            return Reference(ref=f'#/components/schemas/{title}')

        return self._convert_json_schema(json_schema)

    # TODO: Extract other parts of schema

    def _extract_media_type(self, type_: Any) -> MediaType:
        """Extract MediaType with schema."""
        return MediaType(schema=self.extract_schema(type_))
