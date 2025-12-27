from typing import ClassVar, final

from django_modern_rest.controller import BlueprintsT, Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer
from examples.using_controller.blueprints import (
    UserCreateBlueprint,
    UserListBlueprint,
)


@final
class ComposedController(Controller[PydanticSerializer]):
    blueprints: ClassVar[BlueprintsT] = [
        UserListBlueprint,
        UserCreateBlueprint,
    ]


# run: {"controller": "ComposedController", "method": "get"}  # noqa: ERA001, E501
# run: {"controller": "ComposedController", "method": "post", "body": {"email": "user@wms.org", "age": 10}}  # noqa: ERA001, E501
