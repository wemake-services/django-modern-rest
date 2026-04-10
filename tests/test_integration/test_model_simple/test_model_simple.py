from http import HTTPStatus

import pytest
from dirty_equals import IsDatetime, IsPositiveInt
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.test import DMRClient


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:model_simple:user_minimalistic'),
        reverse('api:model_simple:user_detailed'),
    ],
)
def test_user_create_models_example(
    dmr_client: DMRClient,
    faker: Faker,
    *,
    url: str,
) -> None:
    """Ensure that model route works."""
    request_data = {
        'email': faker.email(),
        'customer_service_uid': faker.uuid4(),
    }
    response = dmr_client.post(url, data=request_data)

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        **request_data,
        'id': IsPositiveInt,
        'created_at': IsDatetime(iso_string=True),
    }

    response = dmr_client.get(url)

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    response_json = response.json()
    assert len(response_json) == 1
    assert response_json[0] == {
        **request_data,
        'id': IsPositiveInt,
        'created_at': IsDatetime(iso_string=True),
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        reverse('api:model_simple:user_minimalistic'),
        reverse('api:model_simple:user_detailed'),
    ],
)
def test_user_create_unique_email_error(
    dmr_client: DMRClient,
    faker: Faker,
    *,
    url: str,
) -> None:
    """Ensure that unique email error is handled."""
    request_data = {
        'email': faker.email(),
        'customer_service_uid': faker.uuid4(),
    }
    dmr_client.post(url, data=request_data)
    response = dmr_client.post(url, data=request_data)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == snapshot({
        'detail': [
            {
                'msg': 'User `email` and `customer_service_uid` must be unique',
                'type': 'value_error',
            },
        ],
    })
