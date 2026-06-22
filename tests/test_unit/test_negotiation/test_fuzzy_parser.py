from typing import Any

import pytest
from django.http import HttpRequest
from typing_extensions import override

from dmr import Body, Controller
from dmr.parsers import DeserializeFunc, Parser, Raw
from dmr.plugins.pydantic import PydanticSerializer
from dmr.test import DMRRequestFactory


class _RaisingTestParser(Parser):
    __slots__ = ()

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> Any:
        raise RuntimeError(type(self).__name__)


class _MainStar(_RaisingTestParser):
    __slots__ = ()

    content_type = '*/whatever'


class _SubStar(_RaisingTestParser):
    __slots__ = ()

    content_type = 'application/*'


class _AllStar(_RaisingTestParser):
    __slots__ = ()

    content_type = '*/*'


class _JsonExact(_RaisingTestParser):
    __slots__ = ()

    content_type = 'application/json'


@pytest.mark.parametrize(
    ('headers', 'match'),
    [
        ({'Content-Type': 'application/whatever'}, '_SubStar'),
        ({'Content-Type': 'application/xml'}, '_SubStar'),
        ({'Content-Type': 'text/whatever'}, '_MainStar'),
        ({'Content-Type': 'image/whatever'}, '_MainStar'),
        ({'Content-Type': 'application/json'}, '_JsonExact'),
        ({'Content-Type': 'image/png'}, '_AllStar'),
    ],
)
@pytest.mark.parametrize(
    'parser_types',
    [
        [_MainStar(), _JsonExact(), _AllStar(), _SubStar()],
        [_SubStar(), _MainStar(), _JsonExact(), _AllStar()],
        [_SubStar(), _MainStar(), _AllStar(), _JsonExact()],
        [_JsonExact(), _SubStar(), _MainStar(), _AllStar()],
    ],
)
def test_correct_parser_selected(
    dmr_rf: DMRRequestFactory,
    *,
    headers: dict[str, str],
    match: str,
    parser_types: list[Parser],
) -> None:
    """Ensures we can select correct fuzzy parsers."""

    class _Controller(
        Controller[PydanticSerializer],
    ):
        parsers = parser_types

        def post(self, parsed_body: Body[dict[str, str]]) -> dict[str, str]:
            raise NotImplementedError

    request = dmr_rf.post(
        '/whatever/',
        headers=headers,
        data={},
    )

    with pytest.raises(RuntimeError, match=match):
        _Controller.as_view()(request)
