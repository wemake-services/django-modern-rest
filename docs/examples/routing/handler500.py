import pydantic

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, build_500_handler, path


class UserCreateModel(pydantic.BaseModel):
    email: str


class UserController(Controller[PydanticSerializer]):
    async def post(self, parsed_body: Body[UserCreateModel]) -> UserCreateModel:
        if parsed_body.email.endswith('@old-domain.com'):
            raise RuntimeError('This error will be handled by handler500')
        return parsed_body


router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)

urlpatterns = [
    router.to_urlpatterns(namespace='api'),
]

handler500 = build_500_handler(router.prefix, serializer=PydanticSerializer)

# run: {"controller": "UserController", "method": "post", "body": {"email": "correct@example.com"}, "url": "/api/user/", "use_urlpatterns": true}  # noqa: ERA001, E501
# run: {"controller": "UserController", "method": "post", "body": {"email": "correct@old-domain.com"}, "url": "/api/user/", "use_urlpatterns": true, "curl_args": ["-D", "-"], "assert-error-text": "Internal server error", "fail-with-body": false}  # noqa: ERA001, E501
