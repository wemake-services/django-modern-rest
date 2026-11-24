from typing import Final, Literal

import pytest

from dmr.openapi.breaking import Change, find_breaking_changes
from dmr.openapi.mappers.schema_normalization import DumpedSchema

_JSON: Final = 'application/json'
_STRING: Final[DumpedSchema] = {'type': 'string'}  # noqa: WPS407
_INTEGER: Final[DumpedSchema] = {'type': 'integer'}  # noqa: WPS407
_TOKEN: Final[DumpedSchema] = {  # noqa: WPS407
    'type': 'apiKey',
    'name': 'X-Token',
    'in': 'header',
}
_BEARER: Final[DumpedSchema] = {'type': 'http', 'scheme': 'Bearer'}  # noqa: WPS407
_OAUTH: Final[DumpedSchema] = {'type': 'oauth2', 'flows': {}}  # noqa: WPS407
_SECURITY_LOCATION: Final = '#/paths/~1users/post/security'
_TOTAL: Final = 'X-Total'
_HEADERS_LOCATION: Final = '#/paths/~1users/post/responses/200/headers'


def _media(schema: DumpedSchema, media_type: str = _JSON) -> DumpedSchema:
    return {'content': {media_type: {'schema': schema}}}


def _parameter(
    name: str,
    *,
    location: str = 'query',
    required: bool = False,
    schema: DumpedSchema = _STRING,
) -> DumpedSchema:
    return {
        'name': name,
        'in': location,
        'required': required,
        'schema': schema,
    }


def _operation(
    *,
    body: DumpedSchema | None = None,
    parameters: list[DumpedSchema] | None = None,  # noqa: WPS110
    security: list[DumpedSchema] | None = None,
) -> DumpedSchema:
    operation: DumpedSchema = {'responses': {'200': {'description': 'ok'}}}
    if security is not None:
        operation['security'] = security
    if body is not None:
        operation['requestBody'] = {'required': True, **_media(body)}
    if parameters is not None:
        operation['parameters'] = parameters
    return operation


def _responding(
    schema: DumpedSchema,
    *,
    key: str = 'schema',
) -> DumpedSchema:
    return {
        'responses': {
            '200': {'description': 'ok', 'content': {_JSON: {key: schema}}},
        },
    }


def _spec(paths: DumpedSchema, **components: DumpedSchema) -> DumpedSchema:
    return {
        'openapi': '3.1.0',
        'info': {'title': 'test', 'version': '1'},
        'paths': paths,
        'components': components,
    }


def _secured(
    *security: DumpedSchema,
    **schemes: DumpedSchema,
) -> DumpedSchema:
    return _spec(
        {'/users': {'post': _operation(security=list(security))}},
        securitySchemes=schemes,
    )


_ROOT_SECURED: Final[DumpedSchema] = {  # noqa: WPS407
    **_spec(
        {'/users': {'post': _operation()}},
        securitySchemes={'token': _TOKEN},
    ),
    'security': [{'token': []}],
}


def _ref(section: str, name: str) -> DumpedSchema:
    return {'$ref': f'#/components/{section}/{name}'}


def _header(
    *,
    required: bool = True,
    schema: DumpedSchema = _STRING,
) -> DumpedSchema:
    return {'required': required, 'schema': schema}


def _sending(headers: DumpedSchema, **components: DumpedSchema) -> DumpedSchema:
    response = {'description': 'ok', 'headers': headers}
    return _spec(
        {'/users': {'post': {'responses': {'200': response}}}},
        headers=components,
    )


@pytest.mark.parametrize(
    ('old', 'new'),
    [
        pytest.param(
            _spec({'/users': {'get': _operation()}}),
            _spec({'/users': {'get': _operation(), 'post': _operation()}}),
            id='operation-added',
        ),
        pytest.param(
            _spec({'/users': {'summary': 'Users', 'get': _operation()}}),
            _spec({'/users': {'get': _operation()}}),
            id='non-operation-key-removed',
        ),
        pytest.param(
            _spec({
                '/users/{id}': {
                    'get': _operation(
                        parameters=[
                            {
                                'name': 'id',
                                'in': 'path',
                                'required': True,
                                'schema': _INTEGER,
                            },
                        ],
                    ),
                },
            }),
            _spec({
                '/users/{user_id}': {
                    'get': _operation(
                        parameters=[
                            {
                                'name': 'user_id',
                                'in': 'path',
                                'required': True,
                                'schema': _INTEGER,
                            },
                        ],
                    ),
                },
            }),
            id='path-parameter-renamed',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'post': {
                        'requestBody': _media(_STRING),
                        'responses': {'200': _media(_STRING)},
                    },
                },
            }),
            _spec({
                '/users': {
                    'post': {
                        'requestBody': {
                            'content': {
                                _JSON: {'schema': _STRING},
                                'application/xml': {'schema': _INTEGER},
                            },
                        },
                        'responses': {
                            '200': {
                                'content': {
                                    _JSON: {'schema': _STRING},
                                    'application/xml': {'schema': _INTEGER},
                                },
                            },
                        },
                    },
                },
            }),
            id='media-type-added',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'get': {
                        'responses': {
                            '200': _media(_STRING),
                            '404': _media(_STRING),
                        },
                    },
                },
            }),
            _spec({
                '/users': {'get': {'responses': {'200': _media(_STRING)}}},
            }),
            id='documented-status-removed',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'get': {
                        'responses': {
                            '4XX': _media(_STRING),
                            'default': _media(_INTEGER),
                        },
                    },
                },
            }),
            _spec({
                '/users': {
                    'get': {
                        'responses': {
                            '404': _media(_STRING),
                            '500': _media(_INTEGER),
                        },
                    },
                },
            }),
            id='status-covered-by-range-or-default',
        ),
        pytest.param(
            _spec({'/users': {'get': {'responses': {'200': _media(_STRING)}}}}),
            _spec({
                '/users': {
                    'get': {
                        'responses': {
                            '200': _media(_STRING),
                            'x-internal': {'owner': 'team'},
                        },
                    },
                },
            }),
            id='responses-extension-added',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'post': {
                        'requestBody': {
                            'content': {
                                _JSON: {'schema': _STRING},
                                'text/plain': {'schema': _STRING},
                            },
                        },
                        'responses': {},
                    },
                },
            }),
            _spec({
                '/users': {
                    'post': {
                        'requestBody': {
                            'content': {
                                'application/*': {'schema': _STRING},
                                '*/*': {'schema': _STRING},
                            },
                        },
                        'responses': {},
                    },
                },
            }),
            id='request-media-type-covered-by-range',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'post': {
                        'requestBody': _media(_STRING),
                        'responses': {'200': _media(_STRING)},
                    },
                },
            }),
            _spec({
                '/users': {
                    'post': {
                        'requestBody': _media(
                            _STRING,
                            'Application/JSON; charset=utf-8',
                        ),
                        'responses': {
                            '200': _media(
                                _STRING,
                                'Application/JSON; charset=utf-8',
                            ),
                        },
                    },
                },
            }),
            id='media-type-written-differently',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'get': {
                        'responses': {
                            '200': {
                                'content': {
                                    'application/*': {'schema': _STRING},
                                    '*/*': {'schema': _STRING},
                                },
                            },
                        },
                    },
                },
            }),
            _spec({'/users': {'get': {'responses': {'200': _media(_STRING)}}}}),
            id='response-media-type-range-narrowed',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'get': {
                        'responses': {
                            'default': _media(_STRING),
                            'x-internal': _media(_STRING, 'application/xml'),
                        },
                    },
                },
            }),
            _spec({
                '/users': {'get': {'responses': {'default': _media(_STRING)}}},
            }),
            id='responses-extension-removed',
        ),
        pytest.param(
            _spec({'/users': {'get': _operation()}}),
            _spec({
                '/users': {'get': _operation(parameters=[_parameter('q')])},
            }),
            id='optional-parameter-added',
        ),
        pytest.param(
            _spec(
                {'/users': {'get': _operation(parameters=[_parameter('q')])}},
            ),
            _spec(
                {
                    '/users': {
                        'get': _operation(parameters=[_ref('parameters', 'Q')]),
                    },
                },
                parameters={
                    'Q': _ref('parameters', 'Shared'),
                    'Shared': _parameter('q'),
                },
            ),
            id='parameter-moved-to-components',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'get': _operation(
                        parameters=[_parameter('q', required=True)],
                    ),
                },
            }),
            _spec({
                '/users': {
                    'parameters': [_parameter('q')],
                    'get': _operation(),
                },
            }),
            id='parameter-became-optional',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'get': _operation(
                        parameters=[
                            _parameter(
                                'X-Token',
                                location='header',
                                required=True,
                            ),
                        ],
                    ),
                },
            }),
            _spec({
                '/users': {
                    'get': _operation(
                        parameters=[
                            _parameter(
                                'x-token',
                                location='header',
                                required=True,
                            ),
                        ],
                    ),
                },
            }),
            id='header-parameter-case-changed',
        ),
        pytest.param(
            _spec({'/users': {'post': _operation(body=_STRING)}}),
            _spec({
                '/users': {
                    'post': _operation(body={'type': ['string', 'integer']}),
                },
            }),
            id='request-schema-widened',
        ),
        pytest.param(
            _spec({
                '/users': {'get': _responding({'type': ['string', 'null']})},
            }),
            _spec({'/users': {'get': _responding(_STRING)}}),
            id='response-schema-narrowed',
        ),
        pytest.param(
            _spec({'/users': {'post': _operation(body=_STRING)}}),
            _spec({
                '/users': {'post': _operation(body={'anyOf': [_STRING]})},
            }),
            id='schema-written-differently',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'get': _operation(
                        parameters=[_parameter('q', schema={'enum': ['a']})],
                    ),
                },
            }),
            _spec({
                '/users': {'get': _operation(parameters=[_parameter('q')])},
            }),
            id='parameter-schema-widened',
        ),
        pytest.param(
            _spec({'/users': {'get': _responding(_STRING)}}),
            _spec({'/users': {'get': _responding(_STRING, key='itemSchema')}}),
            id='response-schema-became-item-schema',
        ),
        pytest.param(
            _secured({'token': []}, token=_TOKEN),
            _secured(token=_TOKEN),
            id='security-removed',
        ),
        pytest.param(
            _secured({'token': []}, token=_TOKEN),
            _secured({'token': []}, {'jwt': []}, token=_TOKEN, jwt=_BEARER),
            id='security-alternative-added',
        ),
        pytest.param(
            _secured({'token': []}, {'jwt': []}, token=_TOKEN, jwt=_BEARER),
            _secured(
                {'api_key': []},
                {'bearer': []},
                api_key={**_TOKEN, 'name': 'x-token', 'description': 'Key'},
                bearer={**_BEARER, 'scheme': 'bearer'},
            ),
            id='security-scheme-renamed',
        ),
        pytest.param(
            _secured({'oauth': ['read', 'write']}, oauth=_OAUTH),
            _secured({'oauth': ['read']}, oauth=_OAUTH),
            id='security-scope-removed',
        ),
        pytest.param(
            _ROOT_SECURED,
            _secured({'token': []}, token=_TOKEN),
            id='security-moved-to-operation',
        ),
        pytest.param(
            _secured({'token': [], 'jwt': []}, token=_TOKEN, jwt=_BEARER),
            _secured({'token': []}, token=_TOKEN, jwt=_BEARER),
            id='security-scheme-removed-from-requirement',
        ),
        pytest.param(
            _secured(
                {'first': ['admin'], 'second': []},
                first=_BEARER,
                second=_BEARER,
            ),
            _secured({'first': ['admin']}, first=_BEARER),
            id='security-same-credential-twice',
        ),
        pytest.param(
            _sending({}),
            _sending({_TOTAL: _header()}),
            id='response-header-added',
        ),
        pytest.param(
            _sending({_TOTAL: _header(required=False)}),
            _sending({}),
            id='optional-response-header-removed',
        ),
        pytest.param(
            _sending({_TOTAL: _header(required=False)}),
            _sending({_TOTAL: _header()}),
            id='response-header-became-required',
        ),
        pytest.param(
            _sending({_TOTAL: _header()}),
            _sending({'x-total': _header()}),
            id='response-header-name-case-changed',
        ),
        pytest.param(
            _sending({_TOTAL: _header(schema={'type': ['string', 'null']})}),
            _sending({_TOTAL: _header()}),
            id='response-header-schema-narrowed',
        ),
        pytest.param(
            _sending({_TOTAL: _header()}),
            _sending({_TOTAL: _ref('headers', 'Total')}, Total=_header()),
            id='response-header-moved-to-components',
        ),
        pytest.param(
            _sending({'Set-Cookie: token': _header()}),
            _sending({'set-cookie: token': _header()}),
            id='response-cookie-header-name-case-changed',
        ),
        pytest.param(
            _sending({'Content-Type': _header()}),
            _sending({}),
            id='response-content-type-header-removed',
        ),
    ],
)
def test_compatible(*, old: DumpedSchema, new: DumpedSchema) -> None:
    """Ensures that compatible changes are not reported."""
    assert find_breaking_changes(old, new) == []


def _change(
    location: str,
    message: str,
    *,
    direction: Literal['request', 'response'] = 'request',
    level: Literal['breaking', 'unknown'] = 'breaking',
) -> Change:
    return Change(
        level=level,
        direction=direction,
        location=location,
        message=message,
        operations=('POST /users',),
    )


@pytest.mark.parametrize(
    ('old', 'new', 'expected'),
    [
        pytest.param(
            _spec({'/users': {'get': _operation(), 'post': _operation()}}),
            _spec({'/users': {'get': _operation()}}),
            [_change('#/paths/~1users/post', 'operation removed')],
            id='one-operation-removed',
        ),
        pytest.param(
            _spec({'/users': {'post': _operation()}}),
            _spec({}),
            [_change('#/paths/~1users/post', 'operation removed')],
            id='path-removed',
        ),
        pytest.param(
            _spec({'/users': {'post': _operation()}}),
            _spec({'/users': {'post': _operation(body=_STRING)}}),
            [
                _change(
                    '#/paths/~1users/post/requestBody',
                    'required request body added',
                ),
            ],
            id='required-request-body-added',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'post': {'requestBody': _media(_STRING), 'responses': {}},
                },
            }),
            _spec({
                '/users': {
                    'post': {
                        'requestBody': {'required': True, **_media(_STRING)},
                        'responses': {},
                    },
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/requestBody',
                    'request body became required',
                ),
            ],
            id='request-body-became-required',
        ),
        pytest.param(
            _spec({'/users': {'post': _operation(body=_STRING)}}),
            _spec({'/users': {'post': _operation()}}),
            [
                _change(
                    '#/paths/~1users/post/requestBody',
                    'request body removed',
                ),
            ],
            id='request-body-removed',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'post': {'requestBody': _media(_STRING), 'responses': {}},
                },
            }),
            _spec({
                '/users': {
                    'post': {
                        'requestBody': _media(_STRING, 'application/xml'),
                        'responses': {},
                    },
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/requestBody/content/application~1json',
                    'media type removed',
                ),
            ],
            id='request-media-type-removed',
        ),
        pytest.param(
            _spec({
                '/users': {'post': {'responses': {'200': _media(_STRING)}}},
            }),
            _spec({
                '/users': {'post': {'responses': {'201': _media(_STRING)}}},
            }),
            [
                _change(
                    '#/paths/~1users/post/responses/201',
                    'status code added',
                    direction='response',
                ),
            ],
            id='status-code-added',
        ),
        pytest.param(
            _spec({
                '/users': {'post': {'responses': {'200': _media(_STRING)}}},
            }),
            _spec({
                '/users': {
                    'post': {
                        'responses': {
                            '200': _media(_STRING, 'application/xml'),
                        },
                    },
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/responses/200/content/application~1json',
                    'media type removed',
                    direction='response',
                ),
            ],
            id='response-media-type-removed',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'post': {
                        'responses': {
                            '400': _media(_STRING),
                            '404': _media(_STRING),
                        },
                    },
                },
            }),
            _spec({
                '/users': {'post': {'responses': {'4XX': _media(_STRING)}}},
            }),
            [
                _change(
                    '#/paths/~1users/post/responses/4XX',
                    'status code range added',
                    direction='response',
                ),
            ],
            id='status-code-range-added',
        ),
        pytest.param(
            _spec({
                '/users': {'post': {'responses': {'200': _media(_STRING)}}},
            }),
            _spec({
                '/users': {
                    'post': {
                        'responses': {
                            '200': _media(_STRING),
                            'default': _media(_STRING),
                        },
                    },
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/responses/default',
                    'default response added',
                    direction='response',
                ),
            ],
            id='default-response-added',
        ),
        pytest.param(
            _spec({
                '/users': {'post': {'responses': {'200': _media(_STRING)}}},
            }),
            _spec({
                '/users': {
                    'post': {'responses': {'200': _media(_STRING, '*/*')}},
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/responses/200/content/application~1json',
                    'media type removed',
                    direction='response',
                ),
            ],
            id='response-media-type-replaced-by-range',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'post': {
                        'responses': {
                            '404': _media(_STRING),
                            '4XX': _media(_STRING, 'application/xml'),
                        },
                    },
                },
            }),
            _spec({
                '/users': {
                    'post': {
                        'responses': {
                            '4XX': _media(_STRING, 'application/xml'),
                        },
                    },
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/responses/404/content/application~1json',
                    'media type removed',
                    direction='response',
                ),
            ],
            id='status-code-replaced-by-range',
        ),
        pytest.param(
            _spec({'/users': {'post': _operation()}}),
            _spec({
                '/users': {
                    'post': _operation(
                        parameters=[_parameter('q', required=True)],
                    ),
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/parameters/0',
                    'required query parameter "q" added',
                ),
            ],
            id='required-parameter-added',
        ),
        pytest.param(
            _spec({
                '/users': {'post': _operation(parameters=[_parameter('q')])},
            }),
            _spec({
                '/users': {
                    'post': _operation(
                        parameters=[_parameter('q', required=True)],
                    ),
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/parameters/0',
                    'query parameter "q" became required',
                ),
            ],
            id='parameter-became-required',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'parameters': [_parameter('q')],
                    'post': _operation(),
                },
            }),
            _spec({'/users': {'post': _operation()}}),
            [
                _change(
                    '#/paths/~1users/parameters/0',
                    'query parameter "q" removed',
                ),
            ],
            id='parameter-removed',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'parameters': [_parameter('q')],
                    'post': _operation(),
                },
            }),
            _spec({
                '/users': {
                    'parameters': [_parameter('q')],
                    'post': _operation(
                        parameters=[_parameter('q', required=True)],
                    ),
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/parameters/0',
                    'query parameter "q" became required',
                ),
            ],
            id='operation-parameter-overrides-path-item',
        ),
        pytest.param(
            _spec({'/users': {'post': _operation(body=_STRING)}}),
            _spec({'/users': {'post': _operation(body=_INTEGER)}}),
            [
                _change(
                    '#/paths/~1users/post/requestBody/content/application~1json/schema',
                    'schema accepts fewer values',
                ),
            ],
            id='request-schema-narrowed',
        ),
        pytest.param(
            _spec({'/users': {'post': _responding(_STRING)}}),
            _spec({
                '/users': {'post': _responding({'type': ['string', 'null']})},
            }),
            [
                _change(
                    '#/paths/~1users/post/responses/200/content/application~1json/schema',
                    'schema allows more values',
                    direction='response',
                ),
            ],
            id='response-schema-widened',
        ),
        pytest.param(
            _spec({
                '/users': {'post': _operation(parameters=[_parameter('q')])},
            }),
            _spec({
                '/users': {
                    'post': _operation(
                        parameters=[_parameter('q', schema={'enum': ['a']})],
                    ),
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/parameters/0/schema',
                    'schema accepts fewer values',
                ),
            ],
            id='parameter-schema-narrowed',
        ),
        pytest.param(
            _spec(
                {
                    '/users/{user_id}': {
                        'post': _operation(
                            body={'$ref': '#/components/schemas/User'},
                        ),
                    },
                },
                schemas={'User': {'type': 'object'}},
            ),
            _spec(
                {
                    '/users/{user_id}': {
                        'post': _operation(
                            body={'$ref': '#/components/schemas/User'},
                        ),
                    },
                },
                schemas={'User': {'type': 'object', 'required': ['name']}},
            ),
            [
                Change(
                    level='breaking',
                    direction='request',
                    location=(
                        '#/paths/~1users~1{user_id}/post/requestBody'
                        '/content/application~1json/schema'
                    ),
                    message='schema accepts fewer values',
                    operations=('POST /users/{user_id}',),
                ),
            ],
            id='referenced-schema-narrowed',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'post': _operation(
                        body={'type': 'string', 'pattern': '^a+$'},
                    ),
                },
            }),
            _spec({
                '/users': {
                    'post': _operation(
                        body={'type': 'string', 'pattern': '^(a|b)+$'},
                    ),
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/requestBody/content/application~1json/schema',
                    'schema changed',
                    level='unknown',
                ),
            ],
            id='schema-change-not-proven',
        ),
        pytest.param(
            _spec({
                '/users': {
                    'post': _operation(
                        body={'type': 'string', 'pattern': r'a\Z'},
                    ),
                },
            }),
            _spec({
                '/users': {
                    'post': _operation(
                        body={'type': 'string', 'pattern': r'ab\Z'},
                    ),
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/requestBody/content/application~1json/schema',
                    'schema changed',
                    level='unknown',
                ),
            ],
            id='pattern-not-supported',
        ),
        pytest.param(
            _spec({'/users': {'post': _responding(_STRING, key='itemSchema')}}),
            _spec({
                '/users': {
                    'post': _responding(
                        {'type': ['string', 'null']},
                        key='itemSchema',
                    ),
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/responses/200/content/application~1json/itemSchema',
                    'schema allows more values',
                    direction='response',
                ),
            ],
            id='response-item-schema-widened',
        ),
        pytest.param(
            _spec({'/users': {'post': _operation(body=_STRING)}}),
            _spec({
                '/users': {
                    'post': {
                        **_operation(),
                        'requestBody': {
                            'required': True,
                            **_media(_INTEGER, '*/*'),
                        },
                    },
                },
            }),
            [
                _change(
                    '#/paths/~1users/post/requestBody/content/*~1*/schema',
                    'schema accepts fewer values',
                ),
            ],
            id='request-schema-narrowed-under-range',
        ),
        pytest.param(
            _spec(
                {
                    '/users': {
                        'post': _operation(
                            parameters=[_ref('parameters', 'Q')],
                        ),
                    },
                },
                parameters={'Q': _parameter('q')},
            ),
            _spec(
                {
                    '/users': {
                        'post': _operation(
                            parameters=[_ref('parameters', 'Q')],
                        ),
                    },
                },
                parameters={'Q': _parameter('q', required=True)},
            ),
            [
                _change(
                    '#/components/parameters/Q',
                    'query parameter "q" became required',
                ),
            ],
            id='referenced-parameter-became-required',
        ),
        pytest.param(
            _spec(
                {
                    '/users': {
                        'post': {
                            **_operation(),
                            'requestBody': _ref('requestBodies', 'User'),
                        },
                    },
                },
                requestBodies={'User': _media(_STRING)},
            ),
            _spec(
                {
                    '/users': {
                        'post': {
                            **_operation(),
                            'requestBody': _ref('requestBodies', 'User'),
                        },
                    },
                },
                requestBodies={'User': _media(_INTEGER)},
            ),
            [
                _change(
                    '#/components/requestBodies/User/content/application~1json/schema',
                    'schema accepts fewer values',
                ),
            ],
            id='referenced-request-body-schema-narrowed',
        ),
        pytest.param(
            _spec(
                {
                    '/users': {
                        'post': {'responses': {'200': _ref('responses', 'Ok')}},
                    },
                },
                responses={'Ok': {'description': 'ok', **_media(_STRING)}},
            ),
            _spec(
                {
                    '/users': {
                        'post': {'responses': {'200': _ref('responses', 'Ok')}},
                    },
                },
                responses={
                    'Ok': {
                        'description': 'ok',
                        'content': {_JSON: _ref('mediaTypes', 'Text')},
                    },
                },
                mediaTypes={'Text': {'schema': _INTEGER}},
            ),
            [
                _change(
                    '#/components/mediaTypes/Text/schema',
                    'schema allows more values',
                    direction='response',
                ),
            ],
            id='referenced-response-schema-widened',
        ),
        pytest.param(
            _spec(
                {'/users': _ref('pathItems', 'Users')},
                pathItems={
                    'Users': {'get': _operation(), 'post': _operation()},
                },
            ),
            _spec(
                {'/users': _ref('pathItems', 'Users')},
                pathItems={'Users': {'get': _operation()}},
            ),
            [
                _change(
                    '#/components/pathItems/Users/post',
                    'operation removed',
                ),
            ],
            id='referenced-path-item-operation-removed',
        ),
        pytest.param(
            _spec(
                {
                    '/users': {
                        **_ref('pathItems', 'Users'),
                        'post': _operation(),
                    },
                },
                pathItems={'Users': {'get': _operation()}},
            ),
            _spec(
                {'/users': _ref('pathItems', 'Users')},
                pathItems={'Users': {'get': _operation()}},
            ),
            [_change('#/paths/~1users/post', 'operation removed')],
            id='operation-next-to-path-item-reference-removed',
        ),
        pytest.param(
            _spec(
                {
                    '/users': {
                        **_ref('pathItems', 'Users'),
                        'parameters': [_parameter('q')],
                    },
                },
                pathItems={'Users': {'post': _operation()}},
            ),
            _spec(
                {
                    '/users': {
                        **_ref('pathItems', 'Users'),
                        'parameters': [_parameter('q', required=True)],
                    },
                },
                pathItems={'Users': {'post': _operation()}},
            ),
            [
                _change(
                    '#/paths/~1users/parameters/0',
                    'query parameter "q" became required',
                ),
            ],
            id='parameter-next-to-path-item-reference-became-required',
        ),
        pytest.param(
            _spec({'/users': {'post': _operation()}}),
            _secured({'token': []}, token=_TOKEN),
            [_change(_SECURITY_LOCATION, 'authentication became required')],
            id='security-added',
        ),
        pytest.param(
            _secured({'token': []}, {'jwt': []}, token=_TOKEN, jwt=_BEARER),
            _secured({'jwt': []}, token=_TOKEN, jwt=_BEARER),
            [
                _change(
                    _SECURITY_LOCATION,
                    'authentication with "token" is no longer accepted',
                ),
            ],
            id='security-alternative-removed',
        ),
        pytest.param(
            _secured({'token': []}, token=_TOKEN),
            _secured({'token': [], 'jwt': []}, token=_TOKEN, jwt=_BEARER),
            [
                _change(
                    _SECURITY_LOCATION,
                    'authentication with "token" is no longer accepted',
                ),
            ],
            id='security-scheme-added-to-requirement',
        ),
        pytest.param(
            _secured({'token': []}, token=_TOKEN),
            _secured({'token': []}, token={**_TOKEN, 'name': 'X-Key'}),
            [
                _change(
                    _SECURITY_LOCATION,
                    'authentication with "token" is no longer accepted',
                ),
            ],
            id='security-scheme-changed',
        ),
        pytest.param(
            _secured({'token': []}, token={**_TOKEN, 'in': 'cookie'}),
            _secured(
                {'token': []},
                token={**_TOKEN, 'in': 'cookie', 'name': 'x-token'},
            ),
            [
                _change(
                    _SECURITY_LOCATION,
                    'authentication with "token" is no longer accepted',
                ),
            ],
            id='security-cookie-name-case-changed',
        ),
        pytest.param(
            _secured({'oauth': ['read']}, oauth=_OAUTH),
            _secured({'oauth': ['read', 'write']}, oauth=_OAUTH),
            [
                _change(
                    _SECURITY_LOCATION,
                    'authentication with "oauth" is no longer accepted',
                ),
            ],
            id='security-scope-added',
        ),
        pytest.param(
            _spec({'/users': {'post': _operation()}}),
            _ROOT_SECURED,
            [_change('#/security', 'authentication became required')],
            id='root-security-added',
        ),
        pytest.param(
            _secured({}, {'token': []}, token=_TOKEN),
            _secured({'token': []}, token=_TOKEN),
            [_change(_SECURITY_LOCATION, 'authentication became required')],
            id='security-anonymous-alternative-removed',
        ),
        pytest.param(
            _secured({'token': [], 'jwt': []}, token=_TOKEN, jwt=_BEARER),
            _secured(
                {'token': [], 'oauth': []},
                token=_TOKEN,
                jwt=_BEARER,
                oauth=_OAUTH,
            ),
            [
                _change(
                    _SECURITY_LOCATION,
                    'authentication with "token" and "jwt" '
                    'is no longer accepted',
                ),
            ],
            id='security-scheme-replaced-in-requirement',
        ),
        pytest.param(
            _sending({_TOTAL: _header()}),
            _sending({}),
            [
                _change(
                    f'{_HEADERS_LOCATION}/X-Total',
                    'required response header "X-Total" removed',
                    direction='response',
                ),
            ],
            id='required-response-header-removed',
        ),
        pytest.param(
            _sending({_TOTAL: _header()}),
            _sending({_TOTAL: _header(required=False)}),
            [
                _change(
                    f'{_HEADERS_LOCATION}/X-Total',
                    'response header "X-Total" became optional',
                    direction='response',
                ),
            ],
            id='response-header-became-optional',
        ),
        pytest.param(
            _sending({_TOTAL: _header()}),
            _sending({_TOTAL: _header(schema={'type': ['string', 'null']})}),
            [
                _change(
                    f'{_HEADERS_LOCATION}/X-Total/schema',
                    'schema allows more values',
                    direction='response',
                ),
            ],
            id='response-header-schema-widened',
        ),
        pytest.param(
            _sending({_TOTAL: _ref('headers', 'Total')}, Total=_header()),
            _sending(
                {_TOTAL: _ref('headers', 'Total')},
                Total=_header(required=False),
            ),
            [
                _change(
                    '#/components/headers/Total',
                    'response header "X-Total" became optional',
                    direction='response',
                ),
            ],
            id='response-header-behind-reference-became-optional',
        ),
        pytest.param(
            _sending({'Set-Cookie: Token': _header()}),
            _sending({'Set-Cookie: token': _header()}),
            [
                _change(
                    f'{_HEADERS_LOCATION}/Set-Cookie: Token',
                    'required response header "Set-Cookie: Token" removed',
                    direction='response',
                ),
            ],
            id='response-cookie-name-case-changed',
        ),
    ],
)
def test_breaking(
    *,
    old: DumpedSchema,
    new: DumpedSchema,
    expected: list[Change],
) -> None:
    """Ensures that breaking changes are reported where they happen."""
    assert find_breaking_changes(old, new) == expected


@pytest.mark.parametrize('version', ['3.0.3', '2.0', None])
def test_unsupported_version(*, version: str | None) -> None:
    """Ensures that only OpenAPI 3.1+ is supported."""
    with pytest.raises(ValueError, match=r'3\.1'):
        find_breaking_changes({'openapi': version}, _spec({}))
