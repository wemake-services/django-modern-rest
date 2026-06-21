from typing import final

import pytest
from django.utils.http import parse_header_parameters

from dmr.internal import negotiation


@final
class _Django50MediaType:
    def __init__(self, media_type: str) -> None:
        self.raw = media_type
        full_type, self.params = parse_header_parameters(media_type)
        self.main_type, _, self.sub_type = full_type.partition('/')

    def __str__(self) -> str:
        return self.raw


def test_media_by_precedence_supports_django50_media_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures media ordering works with Django 5.0 ``MediaType``."""
    monkeypatch.setattr(negotiation, 'MediaType', _Django50MediaType)

    ordered_media = negotiation.media_by_precedence(
        (
            'text/plain',
            'application/*;q=0.8',
            'application/json;q=0',
            'application/json;version=1;q=0.2',
            'application/vnd.api+json;q=0.1234',
            'text/html;q=invalid',
            '*/*;q=0.9',
        ),
    )

    assert [str(media_type) for media_type in ordered_media] == [
        'application/json;version=1;q=0.2',
        'text/plain',
        'text/html;q=invalid',
        'application/vnd.api+json;q=0.1234',
        'application/*;q=0.8',
        '*/*;q=0.9',
    ]
