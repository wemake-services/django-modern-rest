from http import HTTPStatus

import pytest
from django.urls import reverse
from faker import Faker

from dmr.test import DMRClient


@pytest.mark.django_db
def test_external_class_success(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that success path works."""
    request_data = {'email': faker.email()}

    response = dmr_client.post(
        reverse('api:external_views:external_class'),
        data=request_data,
    )

    assert response.status_code == HTTPStatus.OK, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == request_data


@pytest.mark.django_db
def test_external_class_bad_method(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that wrong method raises 405."""
    request_data = {'email': faker.email()}

    response = dmr_client.get(
        reverse('api:external_views:external_class'),
        data=request_data,
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED, (
        response.content
    )
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {}


@pytest.mark.django_db
def test_external_class_bad_request(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure that wrong data raises 400."""
    request_data = {'wrong': 'data'}

    response = dmr_client.post(
        reverse('api:external_views:external_class'),
        data=request_data,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {}
