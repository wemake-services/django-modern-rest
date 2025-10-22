from typing import assert_type

import msgspec
from django.http import HttpRequest

from django_modern_rest import Body, Controller, Headers, Query
from django_modern_rest.plugins.msgspec import MsgspecSerializer


class _HeaderModel(msgspec.Struct):
    token: str


# Test that type args work:
_HeaderModel(token=1)  # type: ignore[arg-type]


class _QueryModel(msgspec.Struct):
    search: str


class _MyController(
    Controller[MsgspecSerializer],
    Body[dict[str, int]],
    Headers[_HeaderModel],
    Query[_QueryModel],
):
    def get(self) -> str:
        """All added props have the correct types."""
        assert_type(self.request, HttpRequest)
        assert_type(self.parsed_body, dict[str, int])
        assert_type(self.parsed_headers, _HeaderModel)
        assert_type(self.parsed_query, _QueryModel)
        return 'Done'
