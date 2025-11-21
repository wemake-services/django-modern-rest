from http import HTTPStatus

from django_modern_rest.headers import NewHeader, build_headers
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.response import ResponseModification


def test_build_headers_content_type_missing() -> None:
    """Ensure Content-Type is added when not provided."""
    mod = ResponseModification(
        return_type=str,
        status_code=HTTPStatus.OK,
        headers=None,
        cookies=None,
    )
    headers = build_headers(mod, PydanticSerializer)
    # The serializer should define content_type, e.g. 'application/json'
    assert 'Content-Type' in headers
    assert headers['Content-Type'] == PydanticSerializer.content_type


def test_build_headers_existing_content_type() -> None:
    """Ensure existing Content-Type in modification is not overwritten."""
    mod = ResponseModification(
        return_type=str,
        status_code=HTTPStatus.OK,
        headers={
            'Content-Type': NewHeader(
                description='test header',
                deprecated=False,
                example='text/plain',
                value='text/plain',
            ),
        },
        cookies=None,
    )
    headers = build_headers(mod, PydanticSerializer)
    assert headers['Content-Type'] == 'text/plain'  # unchanged
