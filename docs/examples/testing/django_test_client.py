import uuid
from http import HTTPStatus

from dirty_equals import IsDatetime, IsInt
from django.test import TestCase
from django.urls import reverse


class DjangoTestClientTests(TestCase):
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
