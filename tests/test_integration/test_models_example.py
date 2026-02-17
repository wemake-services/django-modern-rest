from http import HTTPStatus

import pytest
from dirty_equals import IsDatetime, IsPositiveInt
from django.urls import reverse
from faker import Faker

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
        reverse('api:models_example:user_model_create'),
        data=request_data,
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        **request_data,
        'id': IsPositiveInt,
        'created_at': IsDatetime(iso_string=True),
    }
