from typing import Final, Literal

import pytest

from dmr.openapi.breaking import Change, find_breaking_changes
from dmr.openapi.mappers.schema_normalization import DumpedSchema

_JSON: Final = 'application/json'
_STRING: Final[DumpedSchema] = {'type': 'string'}  # noqa: WPS407
_INTEGER: Final[DumpedSchema] = {'type': 'integer'}  # noqa: WPS407


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
) -> DumpedSchema:
    operation: DumpedSchema = {'responses': {'200': {'description': 'ok'}}}
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


def _spec(
    paths: DumpedSchema,
    *,
    schemas: DumpedSchema | None = None,
) -> DumpedSchema:
    return {
        'openapi': '3.1.0',
        'info': {'title': 'test', 'version': '1'},
        'paths': paths,
        'components': {'schemas': schemas or {}},
    }


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
            _spec({
                '/users': {
                    'get': _operation(
                        parameters=[{'$ref': '#/components/parameters/Q'}],
                    ),
                },
            }),
            _spec({
                '/users': {
                    'get': _operation(
                        parameters=[{'$ref': '#/components/parameters/Q'}],
                    ),
                },
            }),
            id='parameter-reference-kept',
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
