from typing import ClassVar

from django_modern_rest import Controller, ResponseSpec
from django_modern_rest.plugins.pydantic import PydanticSerializer
from examples.middleware.csrf_protect_json import csrf_protect_json


@csrf_protect_json
class AsyncController(Controller[PydanticSerializer]):
    """Example async controller using CSRF protection middleware."""

    responses: ClassVar[list[ResponseSpec]] = csrf_protect_json.responses

    async def post(self) -> dict[str, str]:
        # Your async logic here
        return {'message': 'async response'}
