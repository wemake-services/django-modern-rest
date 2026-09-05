from typing import Annotated, Final, final

import pydantic
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django_modern_schemas import MethodSource, ModelSchema
from typing_extensions import TypedDict

from dmr import Body, Controller, Path
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router, path


class UserSchema(ModelSchema[User]):
    # Extra fields can be computed by the model itself:
    full_name: Annotated[str, MethodSource('get_full_name')]

    class Config:
        model = User
        fields = ('id', 'username', 'email')


class UserCreateSchema(ModelSchema[User]):
    class Config:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')


class _UserPath(TypedDict):
    user_id: int


_UserList: Final = pydantic.TypeAdapter(list[UserSchema])


@final
class UsersController(Controller[PydanticSerializer]):
    def get(self) -> list[UserSchema]:
        return _UserList.validate_python(User.objects.all())

    def post(self, parsed_body: Body[UserCreateSchema]) -> UserSchema:
        # Schemas know how to persist themselves:
        return UserSchema.model_validate(parsed_body.save())


@final
class UserDetailController(Controller[PydanticSerializer]):
    def get(self, parsed_path: Path[_UserPath]) -> UserSchema:
        return UserSchema.model_validate(
            get_object_or_404(User, pk=parsed_path['user_id']),
        )


router = Router(
    'api/',
    [
        path('users/', UsersController.as_view(), name='users'),
        path(
            'users/<int:user_id>/',
            UserDetailController.as_view(),
            name='user',
        ),
    ],
)

urlpatterns = [router.to_urlpatterns(namespace='api')]

# run: {"controller": "UsersController", "method": "post", "url": "/api/users/", "body": {"username": "ada", "email": "ada@example.com", "first_name": "Ada", "last_name": "Lovelace"}, "use_urlpatterns": true, "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "UsersController", "method": "get", "url": "/api/users/", "use_urlpatterns": true, "populate_db": true}  # noqa: ERA001, E501
# run: {"controller": "UserDetailController", "method": "get", "url": "/api/users/1/", "use_urlpatterns": true, "populate_db": true}  # noqa: ERA001, E501
