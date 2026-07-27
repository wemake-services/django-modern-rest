import json
import uuid
from http import HTTPStatus

from dirty_equals import IsDatetime, IsInt, IsUUID
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from typing_extensions import override

from dmr.test import DMRClient, DMRRequestFactory
from examples.testing.pydantic_controller import UserController


class TestDMRHelpers(TestCase):
    @override
    def setUp(self) -> None:
        self.client = DMRClient()

    def test_client(self) -> None:
        # See `django_test_app/server/apps/model_simple/views/minimalistic.py`
        request_data = {
            'email': 'test@example.com',
            'customer_service_uid': str(uuid.uuid4()),
        }

        response = self.client.post(
            reverse('api:model_simple:user_minimalistic'),
            data=request_data,
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertEqual(
            response.json(),
            {
                'id': IsInt(),
                'created_at': IsDatetime(iso_string=True),
                **request_data,
            },
        )

    def test_request_factory(self) -> None:
        dmr_rf = DMRRequestFactory()
        payload = {'email': 'user@example.com', 'age': 20}

        request = dmr_rf.post('/users/', data=payload)
        response = UserController.as_view()(request)

        assert isinstance(response, HttpResponse)
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(
            json.loads(response.content),
            {
                'uid': IsUUID,
                **payload,
            },
        )
