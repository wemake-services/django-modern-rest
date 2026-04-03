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


def accepted_type(
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
    accepted_types = sorted(
        [_MediaTypeHeader(typ) for typ in accept_value.split(',')],
        key=_by_priority,
        reverse=True,
    )

    types = [_MediaTypeHeader(typ) for typ in provided_types]

    for accepted in accepted_types:
        for provided in types:
            if provided.match(accepted):
                # Return the accepted type with wildcards replaced
                # by concrete parts from the provided type:
                return provided.as_string(accepted.maintype, accepted.subtype)
    return None


@final
class _MediaTypeHeader:
    """A helper class for ``Accept`` header parsing."""

    __slots__ = ('maintype', 'params_str', 'priority', 'qparams', 'subtype')

    def __init__(self, type_str: str) -> None:
        # preserve the original parameters, because the order might be
        # changed in the dict
        self.params_str = ''.join(type_str.partition(';')[1:])

        full_type, qparams = _parse_content_header(type_str)
        self.qparams = qparams
        maintype, _, subtype = full_type.partition('/')
        self.maintype = maintype
        self.subtype = subtype
        self.priority = self._get_priority()

    def match(self, other: '_MediaTypeHeader') -> bool:
        return next(
            (
                False
                for key, param_value in self.qparams.items()
                if key != 'q' and param_value != other.qparams.get(key)
            ),
            False
            if self.subtype != '*' and other.subtype not in {'*', self.subtype}
            else (
                self.maintype == '*' or other.maintype in {'*', other.maintype}
            ),
        )

    def as_string(self, maintype: str, subtype: str) -> str:
        maintype = maintype if self.maintype == '*' else self.maintype
        subtype = subtype if self.subtype == '*' else self.subtype
        return f'{maintype}/{subtype}{self.params_str}'

    def _get_priority(self) -> tuple[int, int]:  # noqa: WPS231
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


def _by_priority(media: _MediaTypeHeader) -> tuple[int, int]:
    return media.priority


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
