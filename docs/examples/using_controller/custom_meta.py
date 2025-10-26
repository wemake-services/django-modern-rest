from http import HTTPStatus
from typing import final

from django.http import HttpResponse

from django_modern_rest import (
    Controller,
    HeaderDescription,
    ResponseDescription,
    validate,
)
from django_modern_rest.plugins.msgspec import MsgspecSerializer
from django_modern_rest.validation import validate_method_name


@final
class SettingsController(Controller[MsgspecSerializer]):
    def get(self) -> str:
        return 'default get setting'

    def post(self) -> str:
        return 'default post setting'

    @validate(
        ResponseDescription(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            headers={'Allow': HeaderDescription()},
        ),
    )
    def meta(self) -> HttpResponse:
        return self.to_response(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            headers={
                'Allow': ', '.join(
                    validate_method_name(
                        method,
                        allow_custom_http_methods=False,
                    ).upper()
                    for method in sorted(self.api_endpoints.keys())
                ),
            },
        )
