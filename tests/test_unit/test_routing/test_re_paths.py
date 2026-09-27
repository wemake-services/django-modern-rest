from django.urls import re_path

from dmr import Controller
from dmr.openapi import build_schema
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _GetController(Controller[PydanticSerializer]):
    """Test controller with single API endpoint."""

    def get(self) -> str:
        raise NotImplementedError


def test_empty_regex_url_pattern() -> None:
    """Ensure that ``re_path()`` without regex works."""
    router = Router(
        'api//',
        [
            re_path('us/', _GetController.as_view()),
        ],
    )

    schema = build_schema(router).convert()

    assert 'parameters' not in schema['paths']['/api/us/']['get']
