import json
from http import HTTPStatus

from django.test import TestCase
from django.test.utils import override_settings
from django.urls import path

from examples.testing.pydantic_controller import UserController

urlpatterns = [
    path('users/', UserController.as_view(), name='users'),
]


@override_settings(ROOT_URLCONF=__name__)
class TestDjangoBuiltinClient(TestCase):
    def test_post_user(self) -> None:
        payload = {'email': 'user@example.com', 'age': 20}

        response = self.client.post(
            '/users/',
            data=json.dumps(payload),
            content_type='application/json',
        )

        assert response.status_code == HTTPStatus.CREATED
        response_data = json.loads(response.content)
        assert response_data['email'] == payload['email']
        assert response_data['age'] == payload['age']
        assert isinstance(response_data['uid'], str)
