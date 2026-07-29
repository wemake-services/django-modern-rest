import json
import uuid
from http import HTTPStatus

import pytest
from dirty_equals import IsDatetime, IsInt, IsUUID
from django.http import HttpResponse
from django.urls import reverse

from dmr.test import DMRClient, DMRRequestFactory
from examples.testing.pydantic_controller import UserController


@pytest.mark.django_db
def test_client(dmr_client: DMRClient) -> None:
    # See `django_test_app/server/apps/model_simple/views/minimalistic.py`
    request_data = {
        'email': 'test@example.com',
        'customer_service_uid': str(uuid.uuid4()),
    }

    response = dmr_client.post(
        reverse('api:model_simple:user_minimalistic'),
        data=request_data,
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json() == {
        'id': IsInt(),
        'created_at': IsDatetime(iso_string=True),
        **request_data,
    }


def test_request_factory(dmr_rf: DMRRequestFactory) -> None:
    # NOTE: learn how to generated structure random data in the next section:
    request_data = {'email': 'test@example.com', 'age': 43}
    request = dmr_rf.post('/url/', data=request_data)

    response = UserController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.CREATED
    assert response.headers == {'Content-Type': 'application/json'}
    assert json.loads(response.content) == {
        'uid': IsUUID,
        **request_data,
    }
