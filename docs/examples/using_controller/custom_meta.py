from http import HTTPStatus

from django.http import HttpResponse

from dmr import (
    Controller,
    HeaderSpec,
    ResponseSpec,
    validate,
)
from dmr.plugins.msgspec import MsgspecSerializer


class SettingsController(Controller[MsgspecSerializer]):
    def get(self) -> str:
        return 'default get setting'

    def post(self) -> str:
        return 'default post setting'

    # `meta` response is also validated, schema is required:
    @validate(
        ResponseSpec(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            headers={'Allow': HeaderSpec()},
        ),
    )
    def meta(self) -> HttpResponse:  # Handles `OPTIONS` http method
        return self.to_response(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            headers={
                'Allow': ', '.join(
                    method for method in sorted(self.api_endpoints.keys())
                ),
            },
        )


# run: {"controller": "SettingsController", "method": "options", "url": "/api/settings/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
