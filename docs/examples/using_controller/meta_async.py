from dmr import Controller
from dmr.options_mixins import AsyncMetaMixin
from dmr.plugins.pydantic import PydanticSerializer


class AsyncMetaController(
    AsyncMetaMixin,
    Controller[PydanticSerializer],
):
    async def get(self) -> str:
        return 'response from GET'


# run: {"controller": "AsyncMetaController", "method": "options", "url": "/api/settings/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "AsyncMetaController", "openapi_url": "/docs/openapi.json/"}  # noqa: E501, ERA001
