from http import HTTPStatus

from django.urls import reverse
from faker import Faker

from django_modern_rest.test import DMRClient


def test_one_of_email_variant(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure email variant parses and responds correctly."""
    email = faker.email()
    response = dmr_client.post(
        reverse('api:controllers:one_of_blueprint'),
        data={
            'type': 'email',
            'email': email,
            'age': faker.random_int(),
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'variant': 'email', 'value': email}


def test_one_of_phone_variant(
    dmr_client: DMRClient,
    faker: Faker,
) -> None:
    """Ensure phone variant parses and responds correctly."""
    phone = faker.msisdn()
    response = dmr_client.post(
        reverse('api:controllers:one_of_blueprint'),
        data={
            'type': 'phone',
            'phone': phone,
            'age': faker.random_int(),
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {'variant': 'phone', 'value': phone}
