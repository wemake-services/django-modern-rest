from typing import final, override

import pytest
from django.utils.http import parse_header_parameters

from dmr.internal import negotiation


@final
class _Django50MediaType:
    def __init__(self, media_type: str) -> None:
        full_type, media_params = parse_header_parameters(media_type)
        main_type, sub_type = full_type.split('/', maxsplit=1)

        self.raw = media_type
        self.main_type = main_type
        self.sub_type = sub_type
        self._media_params = media_params

    def __getattr__(self, attr_name: str) -> object:
        if attr_name == 'params':
            return self._media_params
        raise AttributeError(attr_name)

    @override
    def __str__(self) -> str:
        return self.raw


def test_django50_media_type_support(
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
