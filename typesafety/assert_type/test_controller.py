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


class _MyController(
    Controller[PydanticSerializer],
    Path[dict[str, int]],
    Headers[_HeaderModel],
    Query[_QueryModel],
):
    def get(self) -> str:
        """All added props have the correct types."""
        assert_type(self.request, HttpRequest)
        assert_type(self.parsed_path, dict[str, int])
        assert_type(self.parsed_headers, _HeaderModel)
        assert_type(self.parsed_query, _QueryModel)
        return 'Done'


class _Handle405Correctly(Controller[PydanticSerializer]):
    def whatever(self, request: HttpRequest) -> None:
        self.http_method_not_allowed(request)  # type: ignore[deprecated]
        self.options(request)  # type: ignore[deprecated]


class _OptionsController(Controller[PydanticSerializer]):
    @override
    def options(self) -> HttpResponse:  # type: ignore[override]
        raise NotImplementedError
