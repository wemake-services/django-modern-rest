import pydantic
from django.urls import include

from dmr import Body, Controller
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, build_404_handler, path


class UserCreateModel(pydantic.BaseModel):
    email: str


class UserController(
    Controller[PydanticSerializer],
):
    async def post(self, parsed_body: Body[UserCreateModel]) -> UserCreateModel:
        return parsed_body


router = Router(
    'api/',
    [
        path('user/', UserController.as_view(), name='users'),
    ],
)

urlpatterns = [
    path(router.prefix, include((router.urls, 'your_app'), namespace='api')),
]

handler404 = build_404_handler(router.prefix, serializer=PydanticSerializer)

# run: {"controller": "UserController", "method": "post", "body": {"email": "correct@example.com"}, "url": "/api/user/", "use_urlpatterns": true}  # noqa: ERA001, E501
# run: {"controller": "UserController", "method": "post", "body": {"email": "correct@old-domain.com"}, "url": "/api/wrong/", "use_urlpatterns": true, "curl_args": ["-D", "-"], "fail-with-body": false}  # noqa: ERA001, E501
