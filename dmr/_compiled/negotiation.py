# Some code here was adapted from Litestar under MIT license
# https://github.com/litestar-org/litestar/blob/main/LICENSE

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
        # Media types with `q=0` are not acceptable at all, we drop them:
        accepted_types = [
            media
            for typ in accept_value.split(',')
            if typ and (media := _MediaTypeHeader(typ)).quality != 0
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
        # Media types with `q=0` are not acceptable at all:
        if accepted.quality != 0:  # noqa: WPS441
            for provided in types:
                if provided.match(accepted):  # noqa: WPS441
                    # Return the accepted type with wildcards replaced
                    # by concrete parts from the provided type:
                    return provided.as_string(
                        accepted.maintype,  # noqa: WPS441
                        accepted.subtype,  # noqa: WPS441
                    )

    return None


def accepted_header(accept_value: str, media_type: str) -> bool:
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

        >>> assert accepted_header('application/json', 'text/plain') is False
        >>> assert (
        ...     accepted_header(
        ...         'application/json,text/html;q=0.8',
        ...         'application/json',
        ...     )
        ...     is True
        ... )
        >>> assert (
        ...     accepted_header('application/json;q=0', 'application/json')
        ...     is False
        ... )

    """
    if not accept_value or not media_type:
        return False

    provided = _MediaTypeHeader(media_type)

    if ',' in accept_value:
        for typ in accept_value.split(','):
            if not typ:
                continue
            accepted = _MediaTypeHeader(typ)
            # Media types with `q=0` are not acceptable at all:
            if accepted.quality != 0 and provided.match(accepted):
                return True
        return False

    accepted = _MediaTypeHeader(accept_value)
    return accepted.quality != 0 and provided.match(accepted)


@final
class _MediaTypeHeader:
    """A helper class for ``Accept`` header parsing."""

    __slots__ = ('maintype', 'params_str', 'qparams', 'quality', 'subtype')

    def __init__(self, type_str: str) -> None:
        if ';' in type_str or _escaped_quote in type_str:
            # preserve the original parameters, because the order might be
            # changed in the dict
            self.params_str = (
                f';{type_str.partition(";")[2]}' if ';' in type_str else ''  # noqa: WPS237
            )
            full_type, qparams = _parse_content_header(type_str)
            self.qparams = qparams
            qparam = qparams.get('q')
            self.quality = (
                _max_quality if qparam is None else _parse_quality(qparam)
            )
        else:
            # Most media types are just `type/subtype`,
            # there are no params to parse and no `q` weight to compute:
            self.params_str = ''
            self.qparams = {}
            self.quality = _max_quality
            full_type = type_str.strip().lower()

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
        qparam = self.qparams.get('q')
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

        return self.quality, specificity


#: Quality is a fixed point value with two decimals,
#: this avoids problems when comparing float values.
_max_quality: Final = 100


def _parse_quality(qparam: str) -> int:
    """
    Return the ``q`` weight of a media type as a fixed point value.

    Malformed and out of range weights are discarded
    and treated as ``1``, the same way
    :class:`django.http.request.MediaType` treats them.
    ``inf`` and ``nan`` are out of range as well,
    so they never reach the int conversion.
    """
    try:
        quality = float(qparam)
    except ValueError:
        return _max_quality
    if not 0 <= quality <= 1:
        return _max_quality
    return int(_max_quality * quality)


_token: Final = r"([\w!#$%&'*+\-.^_`|~]+)"  # noqa: S105
_quoted: Final = r'"([^"]*)"'
_param_re: Final = re.compile(rf';\s*{_token}=(?:{_token}|{_quoted})', re.ASCII)
_escaped_quote: Final = '\\"'
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
    if _escaped_quote in accept:  # only some clients escape quotes
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
