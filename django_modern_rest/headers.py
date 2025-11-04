import dataclasses
from collections import UserDict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, NoReturn, cast, final, override

if TYPE_CHECKING:
    from django_modern_rest.response import ResponseModification
    from django_modern_rest.serialization import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True, init=False)
class _BaseResponseHeader:
    """
    Abstract base class that represents an HTTP header in the response.

    It will be later transformed into
    https://spec.openapis.org/oas/v3.1.0#parameterObject for doc purposes.

    Attributes:
        value: Optional value that can be added to the response headers.
        description: Documentation, why this header is needed and what it does.
        required: Whether this header is required or optional.
        deprecated: Whethere this header is deprecated.
        example: Documentation, what can be given as values in this header.

    """

    # TODO: re-enable schema, examples, content
    # TODO: make `examples` and `example` validation
    # TODO: make sure that we can't set fields like `explode`
    # to other values except default

    description: str | None = None
    deprecated: bool = False
    example: str | None = None


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class NewHeader(_BaseResponseHeader):
    """
    New header that will be added to :class:`django.http.HttpResponse` by us.

    This class is used to add new entries to response's headers.
    Is not used for validation.
    """

    value: str  # noqa: WPS110

    def to_spec(self) -> 'HeaderSpec':
        """Convert header type."""
        namespace = dataclasses.asdict(self)
        namespace.pop('value')
        return HeaderSpec(**namespace, required=True)


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class HeaderSpec(_BaseResponseHeader):
    """
    Existing header that :class:`django.http.HttpResponse` already has.

    This class is used to describe the existing reality.
    Used for validation that all ``required`` headers are present.
    """

    required: bool = True


def build_headers(
    modification: 'ResponseModification',
    serializer: type['BaseSerializer'],
) -> 'HeaderDict':
    """Returns headers with values for raw data endpoints."""
    result_headers = HeaderDict({
        'Content-Type': [serializer.content_type],
    })
    if modification.headers:
        result_headers.update({
            header_name: response_header.value
            for header_name, response_header in modification.headers.items()
        })
    return result_headers


@final
class HeaderDict(UserDict[str, Any]):
    """
    Dictionary-like container for HTTP headers with case-normalized keys.

    Header keys are automatically converted to Title-Case format (e.g.
    ``"content-type"`` → ``"Content-Type"``). Values are stored as lists
    of strings to allow multi-valued headers.

    Examples:
        >>> h = HeaderDict()
        >>> h['content-type'] = 'application/json'
        >>> h['Content-Type']
        'application/json'
        >>> h['ACCEPT'] = 'text/html'
        >>> h['accept'] += ',application/json'
        >>> h['Accept']
        'text/html,application/json'
        >>> h[1]
        Traceback (most recent call last):
            ...
        TypeError: Headers keys must be `str`
        >>> h['x-my-header'] = 1
        Traceback (most recent call last):
            ...
        TypeError: Headers values must be `str` or `Sequence[str]`
    """

    @override
    def __getitem__(self, key: str) -> str:
        """Return the values associated with the key case insensetively."""
        return cast(str, super().__getitem__(self._make_key(key)))

    @override
    def __setitem__(
        self,
        key: str,
        item_to_set: str | Sequence[str] | Any,
    ) -> None:
        """Set values for the given header key case insensetively."""
        is_str = isinstance(item_to_set, str)
        if not is_str and not isinstance(item_to_set, Sequence):
            raise TypeError('Headers values must be `str` or `Sequence[str]`')
        key = self._make_key(key)
        item_to_set = (
            [item_to_set]
            if is_str
            else [str(subitem) for subitem in item_to_set]  # pyright: ignore[reportUnknownVariableType,reportUnknownArgumentType]
        )
        return super().__setitem__(key, ','.join(item_to_set))

    @override
    def __contains__(self, key: object) -> bool:
        """Check if key is present case insensetively."""
        key = self._make_key(key)  # type: ignore[arg-type]  # allow this to raise
        return super().__contains__(key)

    @override
    def __delitem__(self, key: str) -> None:  # noqa: WPS603
        """Delete key from headers case insensetively."""
        return super().__delitem__(self._make_key(key))

    @override
    def __or__(
        self,
        _: Any,
    ) -> NoReturn:
        raise NotImplementedError

    __ior__ = __or__  # pyright: ignore[reportAssignmentType]

    @classmethod
    def _make_key(cls, key: str) -> str:
        if not isinstance(key, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError('Headers keys must be `str`')
        if key.istitle():
            return key
        return key.title()
