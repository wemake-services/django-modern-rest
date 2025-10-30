from typing import ClassVar, final

from django.http import HttpRequest
from django_modern_rest import Controller, ResponseDescription
from django_modern_rest.plugins.pydantic import PydanticSerializer

from project.app.middleware import add_request_id_json  # Don't forget to change


@final
class _RequestWithID(HttpRequest):
    request_id: str


@final
@add_request_id_json
class RequestIdController(Controller[PydanticSerializer]):
    """Controller that uses request_id added by middleware."""

    responses: ClassVar[list[ResponseDescription]] = (
        add_request_id_json.responses
    )

    # Use request with request_id field
    request: _RequestWithID  # type: ignore[mutable-override]

    def get(self) -> dict[str, str]:
        """GET endpoint that returns request_id from modified request."""

        return {
            'request_id': self.request.request_id,
            'message': 'Request ID tracked',
        }
