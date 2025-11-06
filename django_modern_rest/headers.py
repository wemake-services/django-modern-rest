import dataclasses
import sys
import typing
from collections import UserDict
from collections.abc import Iterable, Mapping, Sequence

if typing.TYPE_CHECKING:
    from django_modern_rest.response import ResponseModification
    from django_modern_rest.serialization import BaseSerializer

HeaderLike: typing.TypeAlias = typing.Union['HeaderDict', dict[str, str]]
StrOrIterstr: typing.TypeAlias = str | Iterable[str]


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


@typing.final
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


@typing.final
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
    result_headers = HeaderDict()
    if modification.headers:
        result_headers.update({
            header_name: response_header.value
            for header_name, response_header in modification.headers.items()
        })
    if 'Content-Type' not in result_headers:
        result_headers['Content-Type'] = serializer.content_type
    return result_headers


@typing.final
class HeaderDict(UserDict[str, typing.Any]):  # noqa: WPS214
    """
    Dictionary-like container for HTTP headers with case-normalized keys.

    Header keys are automatically converted to Title-Case format (e.g.
    ``"content-type"`` -> ``"Content-Type"``). Values are stored as strings
    separated by a comma to allow multi-valued headers.

    Use `add(key, val)` or `extend(key, vals)`
    to append values without replacing.

    Examples:
        >>> h = HeaderDict()
        >>> h['content-type'] = 'application/json'
        >>> h['Content-Type']
        'application/json'
        >>> h['ACCEPT'] = 'text/html'
        >>> h.add('accept', 'application/json')
        >>> h['Accept']
        'text/html,application/json'
        >>> h[1]
        Traceback (most recent call last):
            ...
        TypeError: Header keys must be `str`
        >>> h['x-my-header'] = 1
        Traceback (most recent call last):
            ...
        TypeError: Header values must be `str` or `Sequence[str]`
    """

    _titled_keys_cache: typing.ClassVar[dict[str, str]] = {}
    _set_cookie: str = sys.intern('Set-Cookie')

    @typing.override
    def __init__(
        self,
        /,
        pairs: Mapping[str, StrOrIterstr]
        | Iterable[tuple[str, StrOrIterstr]]
        | None = None,
        **kwargs: StrOrIterstr,
    ) -> None:
        """Create a HeaderDict."""
        super().__init__()

        self.update(pairs, **kwargs)

    @typing.override
    def __getitem__(self, key: str) -> str:
        """Return the values associated with the key case insensetively."""
        return typing.cast(str, self.data[self._make_key(key)])

    @typing.override
    def __setitem__(
        self,
        key: str,
        item_to_set: StrOrIterstr | typing.Any,
    ) -> None:
        """Set values for the given header key case insensetively."""
        is_str = isinstance(item_to_set, str)
        if not is_str and not isinstance(item_to_set, (list, tuple, Sequence)):
            raise TypeError('Header values must be `str` or `Sequence[str]`')
        key = self._make_key(key)
        if is_str:
            self.data[key] = item_to_set
        else:
            self.data[key] = ','.join(item_to_set)  # pyright: ignore[reportUnknownArgumentType]

    @typing.override
    def __contains__(self, key: typing.Any) -> bool:
        """Check if key is present case insensetively."""
        return self._make_key(key) in self.data

    @typing.override
    def __delitem__(self, key: str) -> None:  # noqa: WPS603
        """Delete key from headers case insensetively."""
        self.data.pop(self._make_key(key), None)

    @typing.override
    def __or__(self, other: typing.Any) -> typing.NoReturn:
        raise NotImplementedError(
            'Union operations are not supported for HeaderDict',
        )

    __ior__ = __ror__ = __or__  # noqa: WPS429

    @typing.override
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.data})'  # noqa: WPS237

    def add(self, key: str, input_value: StrOrIterstr) -> None:
        """
        Append value(s) to the header `key`. Creates the key if missing.

        - If `value` is a str, it will be split on commas and appended.
        - If `value` is a sequence, each item will be appended.
        """
        key = self._make_key(key)

        if isinstance(input_value, str):
            input_value = input_value.split(',')
        elif isinstance(input_value, (list, tuple, Iterable)):  # pyright: ignore[reportUnnecessaryIsInstance]
            try:
                input_value = [
                    striped
                    for subvalue in input_value
                    if (striped := subvalue.strip())
                ]
            except AttributeError as exc:
                raise TypeError(
                    'Header values must be `str` or `Sequence[str]`',
                ) from exc
        else:
            raise TypeError('Header values must be `str` or `Sequence[str]`')

        if key in self.data:
            self.data[key] = ','.join((self.data[key]).split(',') + input_value)  # noqa: WPS529,WPS221
        else:
            self.data[key] = ','.join(input_value)  # noqa: WPS529

    @typing.override
    def update(  # type: ignore[override]
        self,
        /,
        pairs: Mapping[str, StrOrIterstr]
        | Iterable[tuple[str, StrOrIterstr]]
        | None = None,
        **kwargs: StrOrIterstr,
    ) -> None:
        """Extend using an iterable of pairs appending repeated keys."""
        if pairs:
            for key, input_value in (  # pyright: ignore[reportUnknownVariableType]
                pairs.items() if isinstance(pairs, Mapping) else pairs
            ):
                self.add(key, input_value)  # pyright: ignore[reportUnknownArgumentType,reportArgumentType]

        if kwargs:
            for key, input_value in kwargs.items():
                self.add(key, input_value)

    @classmethod
    def _make_key(cls, key: typing.Any) -> str:
        if not isinstance(key, str):
            raise TypeError('Header keys must be `str`')
        if key in cls._titled_keys_cache:
            return cls._titled_keys_cache[key]  # noqa: WPS529
        if not key.istitle():
            key_titled = key.title()
            cls._titled_keys_cache[key] = key_titled
            key = key_titled
        if sys.intern(key) is cls._set_cookie:
            cls._titled_keys_cache.pop(key)
            raise ValueError(
                'Setting cookies directly via headers is forbidden, use ...',
            )
        return typing.cast(str, key)
