import dataclasses
from http import HTTPStatus
from typing import TYPE_CHECKING

from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.objects import (
    Header,
    MediaType,
    Reference,
    Response,
    Schema,
)

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata, ResponseSpec
    from dmr.serializer import BaseSerializer


def get_schema(
    response_spec: 'ResponseSpec',
    serializer: type['BaseSerializer'],
    context: OpenAPIContext,
    metadata: 'EndpointMetadata',
) -> Response:
    """
    Returns the OpenAPI schema for the response.

    Can be customized in ``ResponseSpec`` subclasses.
    """
    headers: dict[str, Header | Reference] = {}
    headers.update(_get_headers(response_spec, serializer, context))
    headers.update(_get_cookies(response_spec, serializer, context))

    return Response(
        description=response_spec.description
        or HTTPStatus(response_spec.status_code).phrase,
        headers=headers or None,
        content=_get_content(response_spec, serializer, context, metadata),
    )


def _get_headers(
    response_spec: 'ResponseSpec',
    serializer: type['BaseSerializer'],
    context: OpenAPIContext,
) -> dict[str, Header | Reference]:
    if not response_spec.headers:
        return {}

    return {
        name: Header(
            description=header_spec.description,
            deprecated=header_spec.deprecated or None,
            required=header_spec.required or None,
            schema=context.generators.schema(str, serializer),
        )
        for name, header_spec in response_spec.headers.items()
    }


def _get_cookies(
    response_spec: 'ResponseSpec',
    serializer: type['BaseSerializer'],
    context: OpenAPIContext,
) -> dict[str, Header | Reference]:
    # Import cycle:
    if not response_spec.cookies:
        return {}

    cookies: dict[str, Header | Reference] = {}
    for name, cookie_spec in response_spec.cookies.items():
        schema = context.generators.schema(str, serializer)
        # for mypy: `str` cannot return a reference, it is a primitive
        assert isinstance(schema, Schema)  # noqa: S101
        schema = dataclasses.replace(schema, example=f'{name}=123')

        cookies[f'Set-Cookie: {name}'] = Header(
            description=cookie_spec.description,
            required=cookie_spec.required or None,
            schema=schema,
        )
    return cookies


def _get_content(
    response_spec: 'ResponseSpec',
    serializer: type['BaseSerializer'],
    context: OpenAPIContext,
    metadata: 'EndpointMetadata',
) -> dict[str, MediaType]:
    # Import cycle:
    from dmr.negotiation import get_conditional_types  # noqa: PLC0415

    return_types = get_conditional_types(response_spec.return_type) or {}
    return {
        renderer.content_type: MediaType(
            schema=context.generators.schema(
                return_types.get(
                    renderer.content_type,
                    response_spec.return_type,
                ),
                serializer,
                used_for_response=True,
            ),
        )
        for renderer in metadata.renderers.values()
        if (
            not response_spec.limit_to_content_types
            or renderer.content_type in response_spec.limit_to_content_types
        )
    }
