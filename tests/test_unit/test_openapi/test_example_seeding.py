import datetime as dt
from typing import Any

import pydantic
from django.conf import LazySettings
from django.urls import path
from inline_snapshot import snapshot

from dmr import Controller
from dmr.openapi import build_schema
from dmr.openapi.mappers.example import generate_example
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router
from dmr.settings import Settings
from dmr.types import EMPTY


class _SeveralStrings(pydantic.BaseModel):
    first: str
    second: str
    third: str


class _SeedingController(Controller[PydanticSerializer]):
    def get(self) -> _SeveralStrings:
        raise NotImplementedError


def _build_schemas() -> Any:
    return build_schema(
        Router('api/v1/', [path('seeding/', _SeedingController.as_view())]),
    ).convert(skip_validation=True)['components']['schemas']


def test_examples_of_the_same_type_differ(settings: LazySettings) -> None:
    """Ensure that examples come from one stream, not from one seed."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    examples = _build_schemas()['_SeveralStrings']['examples']

    # One generated example, holding a value per model field:
    assert len(examples) == 1
    # All three fields are `str`, they used to get the same value:
    assert len(set(examples[0].values())) == 3


def test_examples_do_not_depend_on_previous_ones(
    settings: LazySettings,
) -> None:
    """Ensure that a schema is reproducible whatever ran before it."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}
    first_build = _build_schemas()

    # The factory is shared state, so this moves its random stream:
    for _ in range(3):
        assert generate_example(str, PydanticSerializer)

    assert _build_schemas() == first_build


def test_examples_are_disabled_by_default(settings: LazySettings) -> None:
    """Ensure that we generate nothing when there is no seed."""
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: EMPTY}

    assert 'examples' not in _build_schemas()['_SeveralStrings']


class _SortedMethodsController(Controller[PydanticSerializer]):
    # `dict` keys are a set with a known iteration order,
    # while `frozenset` order depends on `PYTHONHASHSEED`:
    allowed_http_methods = dict.fromkeys(('delete', 'get', 'put')).keys()

    def get(self) -> int:
        raise NotImplementedError

    def put(self) -> int:
        raise NotImplementedError

    def delete(self) -> int:
        raise NotImplementedError


class _ReversedMethodsController(_SortedMethodsController):
    allowed_http_methods = dict.fromkeys(('put', 'get', 'delete')).keys()


def _build_examples(
    controller: type[Controller[PydanticSerializer]],
) -> dict[str, Any]:
    schema = build_schema(
        Router('api/v1/', [path('methods/', controller.as_view())]),
    ).convert()
    operations = schema['paths']['/api/v1/methods/']
    return {
        method: operation['responses']['200']['content']['application/json']
        for method, operation in operations.items()
    }


def test_examples_do_not_depend_on_methods_order(
    *,
    settings: LazySettings,
) -> None:
    """Ensure that endpoints get examples in the same order every time."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1629
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    assert list(_ReversedMethodsController.api_endpoints) == snapshot([
        'DELETE',
        'GET',
        'PUT',
    ])
    assert _build_examples(_SortedMethodsController) == snapshot({
        'get': {'schema': {'type': 'integer', 'examples': [4895]}},
        'put': {'schema': {'type': 'integer', 'examples': [353]}},
        'delete': {'schema': {'type': 'integer', 'examples': [4185]}},
    })
    assert _build_examples(_ReversedMethodsController) == _build_examples(
        _SortedMethodsController,
    )


class _Event(pydantic.BaseModel):
    created_at: dt.datetime
    day: dt.date
    at: dt.time
    duration: dt.timedelta
    # Hand-written examples are kept, like for any other field.
    # This one is outside of the generated range on purpose:
    deadline: dt.datetime = pydantic.Field(
        examples=[dt.datetime.fromisoformat('2030-01-01T00:00Z')],
    )


class _EventController(Controller[PydanticSerializer]):
    def get(self) -> _Event:
        raise NotImplementedError


def test_date_examples_do_not_depend_on_now(
    settings: LazySettings,
) -> None:
    """Ensure that date and time examples don't change with the clock."""
    # Regression test for
    # https://github.com/wemake-services/django-modern-rest/issues/1632
    settings.DMR_SETTINGS = {Settings.openapi_examples_seed: 5}

    schema = build_schema(
        Router('api/v1/', [path('event/', _EventController.as_view())]),
    ).convert()

    assert schema['components']['schemas']['_Event'] == snapshot({
        'properties': {
            'created_at': {
                'type': 'string',
                'format': 'date-time',
                'title': 'Created At',
            },
            'day': {'type': 'string', 'format': 'date', 'title': 'Day'},
            'at': {'type': 'string', 'format': 'time', 'title': 'At'},
            'duration': {
                'type': 'string',
                'format': 'duration',
                'title': 'Duration',
            },
            'deadline': {
                'type': 'string',
                'format': 'date-time',
                'title': 'Deadline',
                'examples': ['2030-01-01T00:00:00Z'],
            },
        },
        'type': 'object',
        'required': ['created_at', 'day', 'at', 'duration', 'deadline'],
        'title': '_Event',
        'examples': [
            {
                'created_at': '2016-03-12T16:44:15.046152',
                'day': '2019-04-15',
                'at': '22:52:44.444129',
                'duration': 'P6DT10H23M7S',
                'deadline': '2000-10-02T11:06:13.220020',
            },
        ],
    })
