from typing import Final

import pytest
from inline_snapshot import snapshot

from dmr.openapi import OpenAPIConfig, build_schema
from dmr.openapi.objects import (  # noqa: WPS235
    XML,
    Components,
    Discriminator,
    Encoding,
    Example,
    MediaType,
    OAuthFlow,
    OAuthFlows,
    OpenAPIType,
    Parameter,
    Reference,
    Response,
    Schema,
    SecurityScheme,
    Server,
    Tag,
)
from dmr.routing import Router

# Makes sure that the spec we build is validated against the real 3.2 schema:
pytest.importorskip('openapi_spec_validator')

_REUSABLE_MEDIA_TYPE: Final = '#/components/mediaTypes/Reusable'


def _config() -> OpenAPIConfig:
    """Build a config that uses every OpenAPI 3.2 field that we added."""
    return OpenAPIConfig(
        title='OpenAPI 3.2 features',
        version='1.0.0',
        openapi_version='3.2.0',
        self_uri='https://example.com/openapi.json',
        servers=[Server(url='https://example.com', name='production')],
        tags=[
            Tag(name='external', summary='External', kind='audience'),
            Tag(name='partner', parent='external', kind='audience'),
        ],
        components=Components(
            media_types={
                'Reusable': MediaType(
                    description='Reused by several operations',
                    schema=Schema(type=OpenAPIType.STRING),
                    examples={
                        'both-forms': Example(
                            data_value={'key': 'value'},
                            serialized_value='key=value',
                        ),
                    },
                ),
            },
            parameters={
                'Filter': Parameter(
                    name='filter',
                    param_in='querystring',
                    content={
                        'application/x-www-form-urlencoded': MediaType(
                            schema=Schema(type=OpenAPIType.OBJECT),
                            item_encoding=Encoding(
                                content_type='text/plain',
                                prefix_encoding=[
                                    Encoding(content_type='image/png'),
                                ],
                            ),
                        ),
                    },
                ),
            },
            responses={
                'Ok': Response(
                    summary='Ok',
                    description='Everything is fine',
                    content={'text/plain': Reference(ref=_REUSABLE_MEDIA_TYPE)},
                ),
            },
            schemas={
                'Pet': Schema(
                    type=OpenAPIType.OBJECT,
                    xml=XML(name='pet', node_type='element'),
                    discriminator=Discriminator(
                        property_name='petType',
                        mapping={'cat': 'Cat'},
                        default_mapping='OtherPet',
                    ),
                ),
            },
            security_schemes={
                'device': SecurityScheme(
                    type='oauth2',
                    deprecated=True,
                    oauth2_metadata_url='https://example.com/.well-known/oauth',
                    flows=OAuthFlows(
                        device_authorization=OAuthFlow(
                            device_authorization_url='https://example.com/dev',
                            token_url='https://example.com/token',  # noqa: S106
                            scopes={'read': 'Read everything'},
                        ),
                    ),
                ),
            },
        ),
    )


def test_openapi_v32_document_is_valid() -> None:
    """Ensure that all the new 3.2 fields pass the real 3.2 validation."""
    # `convert` validates the result, it raises when something is off:
    dumped = build_schema(Router('api/v1/'), config=_config()).convert()

    assert dumped == snapshot({
        'info': {'title': 'OpenAPI 3.2 features', 'version': '1.0.0'},
        'openapi': '3.2.0',
        '$self': 'https://example.com/openapi.json',
        'servers': [{'url': 'https://example.com', 'name': 'production'}],
        'paths': {},
        'components': {
            'schemas': {
                'Pet': {
                    'type': 'object',
                    'discriminator': {
                        'propertyName': 'petType',
                        'mapping': {'cat': 'Cat'},
                        'defaultMapping': 'OtherPet',
                    },
                    'xml': {'name': 'pet', 'nodeType': 'element'},
                },
            },
            'responses': {
                'Ok': {
                    'description': 'Everything is fine',
                    'content': {
                        'text/plain': {
                            '$ref': '#/components/mediaTypes/Reusable',
                        },
                    },
                    'summary': 'Ok',
                },
            },
            'parameters': {
                'Filter': {
                    'name': 'filter',
                    'in': 'querystring',
                    'content': {
                        'application/x-www-form-urlencoded': {
                            'schema': {'type': 'object'},
                            'itemEncoding': {
                                'contentType': 'text/plain',
                                'prefixEncoding': [
                                    {'contentType': 'image/png'},
                                ],
                            },
                        },
                    },
                },
            },
            'securitySchemes': {
                'device': {
                    'type': 'oauth2',
                    'flows': {
                        'deviceAuthorization': {
                            'tokenUrl': 'https://example.com/token',
                            'scopes': {'read': 'Read everything'},
                            'deviceAuthorizationUrl': 'https://example.com/dev',
                        },
                    },
                    'oauth2MetadataUrl': 'https://example.com/.well-known/oauth',
                    'deprecated': True,
                },
            },
            'mediaTypes': {
                'Reusable': {
                    'schema': {'type': 'string'},
                    'examples': {
                        'both-forms': {
                            'dataValue': {'key': 'value'},
                            'serializedValue': 'key=value',
                        },
                    },
                    'description': 'Reused by several operations',
                },
            },
        },
        'tags': [
            {'name': 'external', 'summary': 'External', 'kind': 'audience'},
            {'name': 'partner', 'parent': 'external', 'kind': 'audience'},
        ],
    })


def test_media_types_components_are_merged() -> None:
    """Ensure that `Components.media_types` take part in the merge."""
    config = OpenAPIConfig(
        title='Media types',
        version='1.0.0',
        openapi_version='3.2.0',
        components=[
            Components(
                media_types={
                    'First': MediaType(schema=Schema(type=OpenAPIType.STRING)),
                },
            ),
            Components(
                media_types={
                    'Second': MediaType(schema=Schema(type=OpenAPIType.NUMBER)),
                },
            ),
        ],
    )

    dumped = build_schema(Router('api/v1/'), config=config).convert()

    assert dumped['components']['mediaTypes'] == snapshot({
        'First': {'schema': {'type': 'string'}},
        'Second': {'schema': {'type': 'number'}},
    })
