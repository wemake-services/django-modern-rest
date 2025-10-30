from typing import ClassVar, final

from django_modern_rest import BlueprintsT, Controller
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
