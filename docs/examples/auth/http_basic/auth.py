from typing import Any, final

from django.conf import settings
from typing_extensions import override

from django_modern_rest import Controller
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.security.http import HttpBasicAsyncAuth
from django_modern_rest.serializer import BaseSerializer


@final
class HttpBasicAsync(HttpBasicAsyncAuth):
    @override
    async def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        username: str,
        password: str,
    ) -> Any | None:
        # Define `HTTP_BASIC_USENAME` and `HTTP_BASIC_PASSWORD`
        # in your settings.py file:
        if (
            username == settings.HTTP_BASIC_USENAME
            and password == settings.HTTP_BASIC_PASSWORD
        ):
            return True
        return None
