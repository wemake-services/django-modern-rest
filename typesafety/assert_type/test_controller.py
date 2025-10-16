from typing import assert_type

import pydantic
from django.http import HttpRequest

from django_modern_rest import Body, Controller, Headers, Query
from django_modern_rest.plugins.pydantic import PydanticSerializer


class _HeaderModel(pydantic.BaseModel):
    token: str


class _QueryModel(pydantic.BaseModel):
    search: str


class _MyController(
    Controller[PydanticSerializer],
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


class _Handle405Correctly(Controller[PydanticSerializer]):
    def whatever(self, request: HttpRequest) -> None:
        self.http_method_not_allowed(request)  # type: ignore[deprecated]
