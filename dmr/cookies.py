# Parts of the code is taken from
# https://github.com/litestar-org/litestar/blob/main/litestar/datastructures/cookie.py
# under MIT license.

# Original license:
# https://github.com/litestar-org/litestar/blob/main/LICENSE

# The MIT License (MIT)

# Copyright (c) 2021, 2022, 2023, 2024, 2025, 2026 Litestar Org.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import dataclasses
from collections.abc import Mapping
from http.cookies import Morsel, SimpleCookie
from typing import TYPE_CHECKING, Any, ClassVar, Literal, final

from django.http import HttpResponseBase

if TYPE_CHECKING:
    from django.utils.functional import (
        _StrOrPromise,  # pyright: ignore[reportPrivateUsage]
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _BaseCookie:
    """Base class for all cookies."""

    path: '_StrOrPromise' = '/'
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
            Can be a lazy string, so a cookie can be scoped
            to a :func:`django.urls.reverse_lazy` url.
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
        skip_validation: Is true, when cookie is only used for schema purposes,
            without any runtime validation. This might be useful, when
            this cookie will be set after our framework's validation.
            For example,
            by :class:`django.contrib.sessions.middleware.SessionMiddleware`
            or by HTTP proxy.
            This cookie might be present in runtime or might be missing.

    .. seealso::

        https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie

    """

    #: This fields are not a part of the `cookie` spec:
    _extra_fields: ClassVar[frozenset[str]] = frozenset((
        'description',
        'required',
        'skip_validation',
    ))

    is_actionable: ClassVar[Literal[False]] = False

    description: '_StrOrPromise | None' = None
    required: bool = True
    skip_validation: bool = False

    def is_equal(self, other: Morsel[str]) -> bool:
        """Compare this object with ``SimpleCookie`` like object."""
        # We have already compared keys, value is not important.
        cookie = SimpleCookie()
        cookie[other.key] = other.value

        namespace = cookie[other.key]
        for field in dataclasses.fields(self):
            if field.name in self._extra_fields:
                continue
            field_name, field_value = self._morsel_field(field.name, other)
            namespace[field_name] = field_value

        return cookie[other.key] == other

    def to_spec(self) -> 'CookieSpec':
        """API for compatibility with ``NewCookie``."""
        return self

    def _morsel_field(
        self,
        field_name: str,
        other: Morsel[str],
    ) -> tuple[str, Any]:
        if field_name == 'expires':
            # It is relative to the current time, can't check it.
            return field_name, other[field_name]
        if field_name == 'max_age':
            # `0` is a real value here: it tells the browser to drop
            # the cookie right away. So, unlike all the other fields,
            # we cannot treat it as a missing one.
            return 'max-age', '' if self.max_age is None else self.max_age
        return field_name, getattr(self, field_name) or ''


@final
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class NewCookie(_BaseCookie):
    """
    New cookie to be set for the response.

    Attributes:
        value: Value for the cookie.
        path: Path fragment that must exist in the request
            url for the cookie to be valid. Defaults to ``/``.
            Can be a lazy string, so a cookie can be scoped
            to a :func:`django.urls.reverse_lazy` url.
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

    is_actionable: ClassVar[Literal[True]] = True

    value: str  # noqa: WPS110

    @classmethod
    def from_spec(cls, spec: CookieSpec, *, value: str) -> 'NewCookie':  # noqa: WPS110
        """
        Create a cookie with *value* that matches the given *spec*.

        Use it when the cookie is described by ``@validate``,
        but its value is only known in runtime.
        Copying the flags by hand would mean two places to keep in sync,
        and a response cookie that does not match its spec
        is a validation error.

        .. versionadded:: 0.15.0
        """
        return cls(
            value=value,
            **{
                field.name: getattr(spec, field.name)
                for field in dataclasses.fields(spec)
                if field.name not in spec._extra_fields  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            },
        )

    def to_spec(self) -> CookieSpec:
        """Converts the modification to spec."""
        namespace = dataclasses.asdict(self)
        namespace.pop('value')
        return CookieSpec(**namespace)

    def as_dict(self) -> dict[str, Any]:
        """Converts to a dictionary ."""
        return dataclasses.asdict(self)


def set_cookies(
    response: HttpResponseBase,
    cookies: Mapping[str, NewCookie] | None,
) -> None:
    """Set cookies for the HTTP response."""
    if cookies:
        for cookie_key, cookie in cookies.items():
            response.set_cookie(cookie_key, **cookie.as_dict())
