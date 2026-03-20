from http import HTTPStatus

from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import condition

from dmr import Controller, HeaderSpec, ResponseSpec
from dmr.decorators import wrap_middleware
from dmr.plugins.pydantic import PydanticSerializer

_ETAG = '"resource-v1"'


def _etag(_: HttpRequest) -> str:
    return _ETAG


@wrap_middleware(
    condition(etag_func=_etag),
    ResponseSpec(
        return_type=dict[str, str],
        status_code=HTTPStatus.OK,
    ),
    ResponseSpec(
        return_type=None,
        status_code=HTTPStatus.NOT_MODIFIED,
        headers={'ETag': HeaderSpec()},
    ),
)
def condition_json(response: HttpResponse) -> HttpResponse:
    """Adds content type for 304 responses to satisfy strict validation."""
    if response.status_code == HTTPStatus.NOT_MODIFIED:
        response.headers['Content-Type'] = 'application/json'
    return response


@condition_json
class ConditionalETagController(Controller[PydanticSerializer]):
    responses = condition_json.responses

    def get(self) -> HttpResponse:
        return self.to_response({'message': 'Fresh content'})


# run: {"controller": "ConditionalETagController", "method": "get", "url": "/api/etag/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# run: {"controller": "ConditionalETagController", "method": "get", "url": "/api/etag/", "headers": {"If-None-Match": "\"resource-v1\""}, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
