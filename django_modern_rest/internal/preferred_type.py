"""
This is a backport of django's feature from 5.2 to older djangos.

All credits go to the original django's authors.
"""

from collections.abc import Sequence

from django.http.request import HttpRequest, MediaType


def get_preferred_type(  # pragma: no cover
    request: HttpRequest,
    media_types: Sequence[str],
) -> str | None:
    """Do not use directly."""
    if not media_types or not request.accepted_types:
        return None

    desired_types = [
        (accepted_type, media_type)
        for media_type in media_types
        if (accepted_type := _accepted_type(request, media_type)) is not None
    ]

    if not desired_types:
        return None

    # Of the desired media types, select the one which is preferred.
    return min(
        desired_types,
        key=lambda typ: request.accepted_types.index(typ[0]),
    )[1]


def _accepted_type(  # pragma: no cover
    request: HttpRequest,
    media_type: str,
) -> MediaType | None:
    media = MediaType(media_type)
    return next(
        (
            accepted_type
            for accepted_type in sorted(
                request.accepted_types,
                key=_media_key,
                reverse=True,
            )
            if media.match(accepted_type)  # type: ignore[arg-type]
        ),
        None,
    )


def _specificity(media: MediaType) -> int:  # pragma: no cover
    if media.main_type == '*':
        return 0
    if media.sub_type == '*':
        return 1

    range_params = media.params.copy()
    range_params.pop('q', None)
    if not range_params:
        return 2
    return 3


def _quality(media: MediaType) -> float:  # pragma: no cover
    try:
        quality = float(media.params.get('q', 1))
    except ValueError:
        # Discard invalid values.
        return 1

    # Valid quality values must be between 0 and 1.
    if quality < 0 or quality > 1:
        return 1

    return round(quality, 3)


def _media_key(media: MediaType) -> tuple[int, float]:  # pragma: no cover
    return _specificity(media), _quality(media)
