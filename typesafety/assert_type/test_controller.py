from typing import assert_type

import pydantic
from django.http import HttpRequest, HttpResponse
from typing_extensions import override

from dmr import Controller, Headers, Path, Query
from dmr.plugins.pydantic import PydanticSerializer


class _HeaderModel(pydantic.BaseModel):
    token: str


class _QueryModel(pydantic.BaseModel):
    search: str


class MyController(Controller[PydanticSerializer]):
    def get(
        self,
        parsed_path: Path[dict[str, int]],
        parsed_headers: Headers[_HeaderModel],
        parsed_query: Query[_QueryModel],
    ) -> str:
        """All added props have the correct types."""
        assert_type(self.request, HttpRequest)
        assert_type(parsed_path, dict[str, int])
        assert_type(parsed_headers, _HeaderModel)
        assert_type(parsed_query, _QueryModel)
        return 'Done'


class Handle405Correctly(Controller[PydanticSerializer]):
    def whatever(self, request: HttpRequest) -> None:
        self.http_method_not_allowed(request)  # type: ignore[deprecated]
        self.options(request)  # type: ignore[deprecated]


class OptionsController(Controller[PydanticSerializer]):
    @override
    def options(self) -> HttpResponse:  # type: ignore[override]
        raise NotImplementedError
