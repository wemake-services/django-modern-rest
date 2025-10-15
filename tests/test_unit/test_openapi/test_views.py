from http import HTTPStatus
from typing import Final

import pytest
from django.http import HttpResponse

from django_modern_rest.openapi.generator import OpenAPISchema
from django_modern_rest.openapi.renderers import JsonRenderer
from django_modern_rest.openapi.views import OpenAPIView
from django_modern_rest.test import DMRRequestFactory

_TEST_SCHEMA: Final[OpenAPISchema] = {  # noqa: WPS407
    'openapi': '3.1.0',
    'info': {'title': 'Test', 'version': '1.0.0'},
    'paths': {},
}
_TEST_PATH: Final[str] = 'test/'


def test_get_with_valid_renderer(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that GET request works with valid renderer and schema."""
    view = OpenAPIView.as_view(
        renderer=JsonRenderer(_TEST_PATH),
        schema=_TEST_SCHEMA,
    )
    response = view(dmr_rf.get(_TEST_PATH))

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK


def test_invalid_renderer_raises_error(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that GET request raises TypeError when renderer is invalid."""
    view_cls = OpenAPIView
    view_cls.renderer = 'not a renderer'  # type: ignore[assignment]
    view_cls.schema = _TEST_SCHEMA

    with pytest.raises(
        TypeError,
        match="Renderer must be a 'BaseRenderer' instance",
    ):
        view_cls().get(dmr_rf.get(_TEST_PATH))


@pytest.mark.parametrize(
    'http_method',
    [
        'post',
        'put',
        'patch',
        'delete',
        'trace',
    ],
)
def test_only_get_method_allowed(
    dmr_rf: DMRRequestFactory,
    *,
    http_method: str,
) -> None:
    """Ensure that only GET method is allowed."""
    view = OpenAPIView.as_view(
        renderer=JsonRenderer(_TEST_PATH),
        schema=_TEST_SCHEMA,
    )
    request_factory_method = getattr(dmr_rf, http_method)
    request = request_factory_method(_TEST_PATH)
    response = view(request)

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
