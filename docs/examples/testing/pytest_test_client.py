import uuid
from http import HTTPStatus

import pytest
from dirty_equals import IsDatetime, IsInt
from django.urls import reverse

from dmr.test import DMRClient


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
