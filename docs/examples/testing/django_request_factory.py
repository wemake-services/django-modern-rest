import json
from http import HTTPStatus

from dirty_equals import IsUUID
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from examples.testing.pydantic_controller import UserController


class DjangoRequestFactoryTests(SimpleTestCase):
    def test_request_factory(self) -> None:
        request_data = {'email': 'test@example.com', 'age': 43}
        request = RequestFactory().post(
            '/users/',
            data=request_data,
            content_type='application/json',
        )

        response = UserController.as_view()(request)

        assert isinstance(response, HttpResponse)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(response.headers, {'Content-Type': 'application/json'})
        self.assertEqual(
            json.loads(response.content),
            {
                'uid': IsUUID,
                **request_data,
            },
        )
