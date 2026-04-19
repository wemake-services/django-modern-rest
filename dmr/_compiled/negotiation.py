# Some code here was adapted from Litestar under MIT license
# https://github.com/litestar-org/litestar/blob/main/LICENSE

# The MIT License (MIT)
#
# Copyright (c) 2021, 2022, 2023, 2024, 2025, 2026 Litestar Org.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import re
from collections.abc import Iterable
from typing import Final, final


def accepted_type(  # noqa: C901
    accept_value: str,
    provided_types: Iterable[str],
) -> str | None:
    """
    Find the best matching media type for the request.

    Args:
        accept_value: Accept's header value.
        provided_types: A list of media types that can be provided
            as a response. These types can contain a wildcard ``*``
            character in the main- or subtype part.

    Returns:
        The best matching media type. If the matching provided
        type contains wildcard characters,
        they are replaced with the corresponding part of the accepted type.
        Otherwise the provided type is returned as-is.

    """
    if not accept_value:
        return None

    types = [_MediaTypeHeader(typ) for typ in provided_types if typ]

    if not types:
        return None

    if ',' in accept_value:
        accepted_types = [
            _MediaTypeHeader(typ) for typ in accept_value.split(',') if typ
        ]
        accepted_types.sort(
            key=lambda media: media.priority,
            reverse=True,
        )
        for accepted in accepted_types:
            for provided in types:
                if provided.match(accepted):
                    # Return the accepted type with wildcards replaced
                    # by concrete parts from the provided type:
                    return provided.as_string(
                        accepted.maintype,
                        accepted.subtype,
                    )
    else:
        accepted = _MediaTypeHeader(accept_value)
        for provided in types:
            if provided.match(accepted):  # noqa: WPS441
                # Return the accepted type with wildcards replaced
                # by concrete parts from the provided type:
                return provided.as_string(accepted.maintype, accepted.subtype)  # noqa: WPS441

    return None


def accepted_header(accept_value: str, media_type: str) -> bool:  # noqa: C901
    """
    Does the client accept a response in the given media type?

    This is a faster alternative to Django's ``HttpRequest.accepts``.

    Args:
        accept_value: The value of ``Accept`` header.
        media_type: The media type to check, e.g. ``"application/json"``.

    Returns:
        ``True`` if the media type is accepted according to the
        ``Accept`` header, otherwise ``False``.

    For example:

        .. code:: python

            >>> from django.http import HttpRequest
            >>> request = HttpRequest()
            >>> request.META = {'HTTP_ACCEPT': 'application/json'}
            >>> accepted_header(
            ...     request.headers.get('Accept'), 'text/plain'
            ... )  # equivalent to request.accepts("text/plain")
            False
            >>> accepted_header(
            ...     'application/json,text/html;q=0.8',
            ...     'application/json',
            ... )  # can be called with any headers-like mapping
            True

    """
    if not accept_value or not media_type:
        return False

    provided = _MediaTypeHeader(media_type)

    if ',' in accept_value:
        for typ in accept_value.split(','):
            if not typ:
                continue
            if provided.match(_MediaTypeHeader(typ)):
                return True
    elif provided.match(_MediaTypeHeader(accept_value)):
        return True

    return False


@final
class _MediaTypeHeader:
    """A helper class for ``Accept`` header parsing."""

    __slots__ = ('maintype', 'params_str', 'qparams', 'subtype')

    def __init__(self, type_str: str) -> None:
        # preserve the original parameters, because the order might be
        # changed in the dict
        self.params_str = (
            f';{type_str.partition(";")[2]}' if ';' in type_str else ''  # noqa: WPS237
        )

        full_type, qparams = _parse_content_header(type_str)
        self.qparams = qparams
        maintype, _, subtype = full_type.partition('/')
        self.maintype = maintype
        self.subtype = subtype

    def match(self, other: '_MediaTypeHeader') -> bool:
        for key, param_value in self.qparams.items():
            if key != 'q' and param_value != other.qparams.get(key):
                return False

        if (
            self.subtype != '*'  # noqa: PLR1714
            and other.subtype != '*'
            and self.subtype != other.subtype
        ):
            return False
        return (
            self.maintype == '*'  # noqa: PLR1714
            or other.maintype == '*'
            or self.maintype == other.maintype
        )

    def as_string(self, maintype: str, subtype: str) -> str:
        maintype = maintype if self.maintype == '*' else self.maintype
        subtype = subtype if self.subtype == '*' else self.subtype
        return f'{maintype}/{subtype}{self.params_str}'

    @property  # don't use cached_property since it's accessed only once
    def priority(self) -> tuple[int, int]:
        # Use fixed point values with two decimals to avoid problems
        # when comparing float values
        quality = 100
        qparam = self.qparams.get('q')
        if qparam is not None:
            try:  # noqa: SIM105
                quality = int(100 * float(qparam))
            except ValueError:
                pass  # noqa: WPS420

        if self.maintype == '*':
            specificity = 0
        elif self.subtype == '*':
            specificity = 1
        elif not self.qparams or (
            qparam is not None and len(self.qparams) == 1
        ):
            # no params or 'q' is the only one which we ignore
            specificity = 2
        else:
            specificity = 3

        return quality, specificity


_token: Final = r"([\w!#$%&'*+\-.^_`|~]+)"  # noqa: S105
_quoted: Final = r'"([^"]*)"'
_param_re: Final = re.compile(rf';\s*{_token}=(?:{_token}|{_quoted})', re.ASCII)
_firefox_quote_escape: Final = re.compile(r'\\"(?!; |\s*$)')


def _parse_content_header(accept: str) -> tuple[str, dict[str, str]]:
    """
    Parse content-type and content-disposition header values.

    Args:
        accept: A header string value to parse.

    Returns:
        A tuple containing the normalized header string
        and a dictionary of parameters.
    """
    accept = _firefox_quote_escape.sub('%22', accept)
    pos = accept.find(';')
    if pos == -1:
        options: dict[str, str] = {}
    else:
        options = {
            media.group(1).lower(): (
                media.group(2) or media.group(3).replace('%22', '"')
            )
            for media in _param_re.finditer(accept[pos:])
        }
        accept = accept[:pos]
    return accept.strip().lower(), options
