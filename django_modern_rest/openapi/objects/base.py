from collections.abc import Iterator
from dataclasses import Field, asdict, dataclass, fields, is_dataclass
from enum import Enum
from typing import Any


@dataclass(frozen=True, kw_only=True, slots=True)
class BaseObject:
    """Base class for schema spec objects."""

    def to_schema(self) -> dict[str, Any]:
        """TODO: add docs."""
        result: dict[str, Any] = {}
        exclude = self._exclude_fields

        for field in self._iter_fields():
            if field.name in exclude:
                continue

            value = _normalize_value(getattr(self, field.name, None))
            if value is not None:
                if 'alias' in field.metadata:
                    if not isinstance(field.metadata['alias'], str):
                        raise TypeError('metadata["alias"] must be a str')
                    key = field.metadata['alias']
                else:
                    key = _normalize_key(field.name)
                result[key] = value

        return result

    # Private API:
    @property
    def _exclude_fields(self) -> set[str]:
        return set()

    def _iter_fields(self) -> Iterator[Field[Any]]:
        yield from fields(self)


def _normalize_key(key: str) -> str:
    if key.endswith('_in'):
        return 'in'
    if key.startswith('schema_'):
        return key.split('_')[1]
    if '_' in key:
        components = key.split('_')
        return components[0] + ''.join(
            component.title() for component in components[1:]
        )
    return '$ref' if key == 'ref' else key


def _normalize_value(value: Any) -> Any:
    if isinstance(value, BaseObject):
        return value.to_schema()
    if is_dataclass(value):
        return {
            _normalize_value(k): _normalize_value(v)
            for k, v in asdict(value).items()  # type: ignore[call-overload]
            if v is not None
        }
    if isinstance(value, dict):
        return {
            _normalize_value(k): _normalize_value(v)
            for k, v in value.items()  # type: ignore[arg-type]
            if v is not None
        }
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]  # type: ignore[arg-type]
    return value.value if isinstance(value, Enum) else value
