from dmr.controller import Controller
from dmr.plugins.pydantic import PydanticSerializer
from examples.using_controller.blueprints import (
    UserCreateBlueprint,
    UserListBlueprint,
)


class ComposedController(Controller[PydanticSerializer]):
    blueprints = (
        UserListBlueprint,
        UserCreateBlueprint,
    )


# run: {"controller": "ComposedController", "method": "get"}  # noqa: ERA001, E501
# run: {"controller": "ComposedController", "method": "post", "body": {"email": "user@wms.org", "age": 10}}  # noqa: ERA001, E501
