from typing import Any

from django.conf import settings
from typing_extensions import override

from dmr import Controller
from dmr.endpoint import Endpoint
from dmr.security.http import HttpBasicAsyncAuth
from dmr.serializer import BaseSerializer


class HttpBasicAsync(HttpBasicAsyncAuth):
    @override
    async def authenticate(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        username: str,
        password: str,
    ) -> Any | None:
        # Define `HTTP_BASIC_USERNAME` and `HTTP_BASIC_PASSWORD`
        # in your settings.py file:
        if (
            username == settings.HTTP_BASIC_USERNAME
            and password == settings.HTTP_BASIC_PASSWORD
        ):
            return True
        return None
