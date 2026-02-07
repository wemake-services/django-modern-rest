from typing import final

from django_modern_rest.plugins.pydantic import PydanticSerializer
from examples.reusable_code.reusable_controller import ReusableController


@final
class PydanticController(ReusableController[PydanticSerializer]):
    """This controller will use pydantic for serialization."""


# run: {"controller": "PydanticController", "method": "get", "url": "/api/example/"}  # noqa: ERA001, E501
