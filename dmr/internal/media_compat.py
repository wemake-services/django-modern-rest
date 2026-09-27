# Compatibility helpers below are copied from
# https://github.com/django/django/blob/main/django/http/request.py

from collections.abc import Iterable

import django
from django.http.request import MediaType

# Django <5.2 does not have `.quality` and `.specificity` media attributes.
# We don't cover the copied functions, because the code is taken
# from the Django. It should be pretty stable.


def media_quality(media: MediaType) -> float:  # pragma: no cover
    """Return media quality that works for all django versions."""
    try:
        return media.quality
    except AttributeError:
        try:  # noqa: WPS505
            quality = float(media.params.get('q', 1))
        except ValueError:
            # Discard invalid values.
            return 1

        # Valid quality values must be between 0 and 1.
        if quality < 0 or quality > 1:
            return 1

        return round(quality, 3)


def media_specificity(media: MediaType) -> float:  # pragma: no cover
    """Return media specificity that works for all django versions."""
    try:
        return media.specificity
    except AttributeError:
        if media.main_type == '*':  # noqa: WPS226
            return 0
        if media.sub_type == '*':
            return 1
        if not media_range_params(media):
            return 2
        return 3


def media_range_params(
    media: MediaType,
) -> dict[str, bytes]:  # pragma: no cover
    """Return media specificity that works for all django versions."""
    try:
        return media.range_params
    except AttributeError:
        range_params = media.params.copy()
        range_params.pop('q', None)
        return range_params


def media_match(  # pragma: no cover  # noqa: C901, WPS210
    media: MediaType,
    content_type: str,
) -> bool:
    """Compatible match method for older Django versions."""
    # TODO: this should be replaced with our own compiled implementation.
    if django.VERSION >= (5, 2):
        return media.match(content_type)

    # For older versions, do the manual work:
    if not content_type:
        return False

    other = MediaType(content_type)
    assert isinstance(other, MediaType)  # noqa: S101

    main_types = [media.main_type, other.main_type]
    sub_types = [media.sub_type, other.sub_type]

    # Main types and sub types must be defined.
    if not all((*main_types, *sub_types)):
        return False

    # Main types must match or one be "*", same for sub types.
    for this_type, other_type in (main_types, sub_types):
        if this_type != other_type and this_type != '*' and other_type != '*':  # noqa: PLR1714
            return False

    media_range = media_range_params(media)
    other_range = media_range_params(other)
    if bool(media_range) == bool(other_range):
        # If both have params or neither have params, they must be
        # identical.
        result = media_range == other_range  # noqa: WPS110
    else:
        # If self has params and other does not, it's a match.
        # If other has params and self does not, don't match.
        result = bool(media_range or not other_range)  # noqa: WPS110
    return result


# Our own helpers, built on top of the compatibility ones above:


def media_by_precedence(content_types: Iterable[str]) -> list[MediaType]:
    """Return sorted content types based on specificity and quality."""
    return sorted(
        (
            media_type
            for content_type in content_types
            if media_quality((media_type := MediaType(content_type))) != 0
        ),
        key=lambda media: (media_specificity(media), media_quality(media)),
        reverse=True,
    )
