import json
from http import HTTPStatus

from dirty_equals import IsUUID
from django.http import HttpResponse
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import path
from typing_extensions import override

from dmr.test import DMRClient, DMRRequestFactory
from examples.testing.pydantic_controller import UserController

urlpatterns = [
    path('users/', UserController.as_view(), name='users'),
]


@override_settings(ROOT_URLCONF=__name__)
class TestDMRHelpers(TestCase):
    @override
    def setUp(self) -> None:
        self.client = DMRClient()

    def test_dmr_client_post_json_by_default(self) -> None:
        payload = {'email': 'user@example.com', 'age': 20}

        response = self.client.post('/users/', data=payload)

        assert isinstance(response, HttpResponse)
        assert response.status_code == HTTPStatus.CREATED
        assert json.loads(response.content) == {
            'uid': IsUUID,
            **payload,
        }

    def test_dmr_request_factory_with_controller(self) -> None:
        dmr_rf = DMRRequestFactory()
        payload = {'email': 'user@example.com', 'age': 20}

        request = dmr_rf.post('/users/', data=payload)
        response = UserController.as_view()(request)

        assert isinstance(response, HttpResponse)
        assert request.content_type == 'application/json'
        assert response.status_code == HTTPStatus.CREATED
        assert json.loads(response.content) == {
            'uid': IsUUID,
            **payload,
        }
