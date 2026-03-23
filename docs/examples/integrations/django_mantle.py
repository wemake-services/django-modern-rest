import attrs

from dmr import Controller
from dmr.plugins.msgspec import MsgspecSerializer


@attrs.define
class _UserModel:
    username: str
    email: str
    is_active: bool


class UsersController(Controller[MsgspecSerializer]):
    def get(self) -> list[_UserModel]:
        # We have to do import here due to how our docs build systems works,
        # but in real apps they must be on the module level:
        from django.contrib.auth.models import User  # noqa: PLC0415
        from mantle import Query  # noqa: PLC0415

        return Query(User.objects.all(), _UserModel).all()


# run: {"controller": "UsersController", "method": "get", "url": "/api/users/", "populate_db": true}  # noqa: ERA001, E501
# openapi: {"controller": "UsersController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
