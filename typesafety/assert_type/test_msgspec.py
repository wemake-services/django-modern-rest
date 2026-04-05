from typing import assert_type

import msgspec
from django.http import HttpRequest

from dmr import Body, Controller, Headers, Query
from dmr.plugins.msgspec import MsgspecSerializer


class _HeaderModel(msgspec.Struct):
    token: str


# Test that type args work:
_HeaderModel(token=1)  # type: ignore[arg-type]


class _QueryModel(msgspec.Struct):
    search: str


class MyController(Controller[MsgspecSerializer]):
    def get(
        self,
        parsed_body: Body[dict[str, int]],
        parsed_headers: Headers[_HeaderModel],
        parsed_query: Query[_QueryModel],
    ) -> str:
        """All added props have the correct types."""
        assert_type(self.request, HttpRequest)
        assert_type(parsed_body, dict[str, int])
        assert_type(parsed_headers, _HeaderModel)
        assert_type(parsed_query, _QueryModel)
        return 'Done'
