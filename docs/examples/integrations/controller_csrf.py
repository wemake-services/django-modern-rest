from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class ExampleController(Controller[PydanticSerializer]):
    csrf_exempt = False

    def post(self) -> str:
        return 'ok'


# run: {"controller": "ExampleController", "method": "post", "url": "/api/example/", "cookies": {"csrftoken": "$CSRF_TOKEN"}, "headers": {"X-CSRFToken": "$CSRF_TOKEN"}, "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# run: {"controller": "ExampleController", "method": "post", "url": "/api/example/", "curl_args": ["-D", "-"], "assert-error-text": "CSRF", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "ExampleController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
