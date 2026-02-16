from django_modern_rest import Blueprint, Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.jwt import JWTSyncAuth


class MyBlueprint(Blueprint[PydanticSerializer]):
    # Has auth:
    auth = (JWTSyncAuth(),)

    def get(self) -> str:
        return 'authed'


class APIController(Controller[PydanticSerializer]):
    blueprints = (MyBlueprint,)

    # Controller's methods won't require any auth:
    def post(self) -> str:
        return 'no auth required'


# run: {"controller": "APIController", "method": "get", "url": "/api/example/", "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
# run: {"controller": "APIController", "method": "post", "url": "/api/example/"}  # noqa: ERA001, E501
