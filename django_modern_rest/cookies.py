# Parts of the code is taken from
# https://github.com/litestar-org/litestar/blob/main/litestar/datastructures/cookie.py
# under MIT license.

import dataclasses
from http.cookies import Morsel, SimpleCookie
from typing import Any, ClassVar, Literal, final


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _BaseCookie:
    """Base class for all cookies."""

    path: str = '/'
    max_age: int | None = None
    expires: int | None = None
    domain: str | None = None
    secure: bool | None = None
    httponly: bool | None = None
    samesite: Literal['lax', 'strict', 'none'] = 'lax'


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CookieSpec(_BaseCookie):
    """
    Description of a single cookie in ``Set-Cookie`` header.

    Attributes:
        path: Path fragment that must exist in the request
            url for the cookie to be valid. Defaults to ``/``.
        max_age: Maximal age of the cookie before its invalidated.
        expires: Seconds from now until the cookie expires.
        domain: Domain for which the cookie is valid.
        secure: Https is required for the cookie.
        httponly: Forbids javascript to access the cookie
            via ``document.cookie``.
        samesite: Controls whether or not a cookie is sent
            with cross-site requests. Defaults to ``'lax'``.
        description: Description of the response cookie header
            for OpenAPI documentation.
        required: Defines that this cookie can be missing in some cases.

    .. seealso::

        https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie

    """

    #: This fields are not a part of the `cookie` spec:
    _extra_fields: ClassVar[frozenset[str]] = frozenset((
        'description',
        'required',
    ))

    description: str | None = None
    required: bool = True

    def is_equal(self, other: Morsel[str]) -> bool:
        """Compare this object with ``SimpleCookie`` like object."""
        # We have already compared keys, value is not important.
        cookie = SimpleCookie()
        cookie[other.key] = other.value

        namespace = cookie[other.key]
        for field in dataclasses.fields(self):
            if field.name in self._extra_fields:
                continue
            if field.name == 'expires':
                # It is relative to the current time, can't check it.
                namespace[field.name] = other[field.name]
                continue
            field_name = 'max-age' if field.name == 'max_age' else field.name
            namespace[field_name] = getattr(self, field.name) or ''

        return cookie[other.key] == other


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class NewCookie(_BaseCookie):
    """
    New cookie to be set for the response.

    Attributes:
        value: Value for the cookie.
        path: Path fragment that must exist in the request
            url for the cookie to be valid. Defaults to ``/``.
        max_age: Maximal age of the cookie before its invalidated.
        expires: Seconds from now until the cookie expires.
        domain: Domain for which the cookie is valid.
        secure: Https is required for the cookie.
        httponly: Forbids javascript to access the cookie
            via ``document.cookie``.
        samesite: Controls whether or not a cookie is sent
            with cross-site requests. Defaults to ``'lax'``.

    .. seealso::

        https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie

    """

    value: str  # noqa: WPS110

    def to_spec(self) -> CookieSpec:
        """Converts the modification to spec."""
        namespace = dataclasses.asdict(self)
        namespace.pop('value')
        return CookieSpec(**namespace)

    def as_dict(self) -> dict[str, Any]:
        """Converts to a dictionary ."""
        return dataclasses.asdict(self)
