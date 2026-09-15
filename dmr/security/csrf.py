from collections.abc import Mapping
from http import HTTPMethod, HTTPStatus
from typing import ClassVar, TYPE_CHECKING

from dmr.errors import ErrorModel
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.serializer import BaseSerializer



def build_csrf_handler():
    # TODO support `ErrorModel` customization
    ...


class CsrfResponseSpecProvider(ResponseSpecProvider):
    # Matches Django's definition in `CsrfViewMiddleware`
    _safe_http_methods: ClassVar[frozenset[HTTPMethod]] = frozenset((
        HTTPMethod.GET,
        HTTPMethod.HEAD,
        HTTPMethod.OPTIONS,
        HTTPMethod.TRACE,
    ))

    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: 'Controller[BaseSerializer]',
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        if (
            controller_cls.csrf_exempt
            or metadata.method in self._safe_http_methods
        ):
            return []

        return self._add_new_response(
            # NOTE: we always return the default error model here, because
            # when `CsrfViewMiddleware` is active, it does not raise an error,
            # it directly calls `CSRF_FAILURE_VIEW` to return a response.
            # If it is configured properly, we would call `build_csrf_handler`
            # to return the response.
            ResponseSpec(
                ErrorModel,
                status_code=HTTPStatus.FORBIDDEN,
                description='Raised when CSRF check failed',
            ),
            existing_responses,
        )
