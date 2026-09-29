from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from examples.middleware.csrf_protect_json import csrf_protect_json


@csrf_protect_json
class AsyncController(Controller[PydanticFastSerializer]):
    """Example async controller using CSRF protection middleware."""

    responses = csrf_protect_json.responses

    async def post(self) -> dict[str, str]:
        # Your async logic here
        return {'message': 'async response'}
