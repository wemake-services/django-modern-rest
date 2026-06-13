from http import HTTPStatus

import pytest
from dirty_equals import IsDatetime, IsList, IsPositiveInt
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.test import DMRClient


@pytest.mark.django_db
def test_user_create_models_example(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that model route works."""
    request_data = {
        'email': faker.email(),
        'role': {'name': faker.name()},
        'tags': [{'name': faker.name()}, {'name': faker.name()}],
    }
    response = dmr_client.post(
        reverse('api:model_fk:user'),
        data=request_data,
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        **request_data,
        'id': IsPositiveInt,
        'tags': IsList(*request_data['tags'], check_order=False),
        'created_at': IsDatetime(iso_string=True),
    }

    response = dmr_client.get(reverse('api:model_fk:user'))

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'count': 1,
        'num_pages': 1,
        'per_page': 10,
        'page': {
            'number': 1,
            'object_list': [
                {
                    **request_data,
                    'id': IsPositiveInt,
                    'tags': IsList(*request_data['tags'], check_order=False),
                    'created_at': IsDatetime(iso_string=True),
                },
            ],
        },
    }


@pytest.mark.django_db
@pytest.mark.parametrize('over_long_field', ['role', 'tag'])
def test_user_create_name_too_long_rejected(
    dmr_client: DMRClient,
    faker: Faker,
    over_long_field: str,
) -> None:
    """Names longer than ``Tag``/``Role`` ``max_length=100`` are rejected.

    Regression for #944: previously the Pydantic schemas did not mirror the
    Django model ``max_length=100`` constraint, so over-long names passed
    validation and failed at the database layer with an unhandled 500
    (PostgreSQL) or were silently truncated (SQLite).
    """
    min_chars = 101
    role_name = (
        faker.pystr(min_chars=min_chars, max_chars=min_chars + 10)
        if over_long_field == 'role'
        else faker.name()
    )
    tag_name = (
        faker.pystr(min_chars=min_chars, max_chars=min_chars + 10)
        if over_long_field == 'tag'
        else faker.name()
    )
    response = dmr_client.post(
        reverse('api:model_fk:user'),
        data={
            'email': faker.email(),
            'role': {'name': role_name},
            'tags': [{'name': tag_name}],
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    payload = response.json()
    assert payload['detail'][0]['type'] == 'value_error'
    assert 'at most 100 characters' in payload['detail'][0]['msg']


@pytest.mark.django_db
def test_user_create_unique_email_error(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that unique email error is handled."""
    email = faker.email()
    request_data = {
        'email': email,
        'role': {'name': faker.name()},
        'tags': [{'name': faker.name()}],
    }

    # First request will succeed:
    response = dmr_client.post(
        reverse('api:model_fk:user'),
        data=request_data,
    )

    assert response.status_code == HTTPStatus.CREATED, response.content

    # Second request will fail:
    response = dmr_client.post(
        reverse('api:model_fk:user'),
        data=request_data,
    )

    assert response.status_code == HTTPStatus.CONFLICT, response.content
    assert response.json() == snapshot({
        'detail': [
            {
                'msg': 'User `email` must be unique',
                'type': 'value_error',
            },
        ],
    })
