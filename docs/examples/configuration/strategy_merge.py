from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.jwt import CookieJWTSyncAuth, HeaderJWTSyncAuth


class APIController(Controller[PydanticSerializer]):
    auth = (HeaderJWTSyncAuth(),)

    @modify(auth=[*auth, CookieJWTSyncAuth()])
    def get(self) -> str:  # has merged auth
        assert self.request.user.is_authenticated
        return 'get'

    def post(self) -> str:  # has auth from the controller level
        assert self.request.user.is_authenticated
        return 'post'


# run: {"controller": "APIController", "method": "get", "url": "/api/users/", "cookies": {"access_token": "$JWT_ACCESS_TOKEN"}, "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "APIController", "method": "get", "url": "/api/users/", "headers": {"Authorization": "Bearer $JWT_ACCESS_TOKEN"}, "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "APIController", "method": "post", "url": "/api/users/", "headers": {"Authorization": "Bearer $JWT_ACCESS_TOKEN"}, "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "APIController", "method": "post", "url": "/api/users/", "cookies": {"access_token": "$JWT_ACCESS_TOKEN"}, "populate_db": true, "assert-error-text": "Not authenticated", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "APIController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001
