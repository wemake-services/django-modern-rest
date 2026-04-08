import django_filters
import pydantic
from django.contrib.auth.models import User

from dmr import Controller, Query
from dmr.plugins.pydantic import PydanticSerializer


class UserFilter(django_filters.FilterSet):
    class Meta:
        model = User
        fields = ('is_active',)


# Create query model for validation and docs:
class QueryModel(pydantic.BaseModel):
    is_active: bool


class UserModel(pydantic.BaseModel):
    username: str
    email: str
    is_active: bool


class UsersController(Controller[PydanticSerializer]):
    def get(self, parsed_query: Query[QueryModel]) -> list[UserModel]:
        # Still pass `.GET` for API compatibility:
        user_filter = UserFilter(
            self.request.GET,
            queryset=User.objects.all(),
        )
        return [
            UserModel.model_validate(user, from_attributes=True)
            for user in user_filter.qs
        ]


# run: {"controller": "UsersController", "method": "get", "url": "/api/users/", "populate_db": true}  # noqa: ERA001, E501
# openapi: {"controller": "UsersController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001
