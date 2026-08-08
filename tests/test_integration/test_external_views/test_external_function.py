from http import HTTPStatus

import pytest
from django.urls import reverse
from faker import Faker
from inline_snapshot import snapshot

from dmr.test import DMRClient


@pytest.mark.django_db
def test_external_function_success(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that success path works."""
    response = dmr_client.get(
        reverse('api:external_views:external_function'),
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == snapshot({'status': 200})


@pytest.mark.django_db
def test_external_function_bad_method(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that wrong method raises 405."""
    response = dmr_client.post(
        reverse('api:external_views:external_function'),
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED, (
        response.content
    )
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {}
