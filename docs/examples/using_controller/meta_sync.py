from dmr import Controller
from dmr.options_mixins import MetaMixin
from dmr.plugins.pydantic import PydanticSerializer


class SyncMetaController(
    MetaMixin,
    Controller[PydanticSerializer],
):
    def get(self) -> str:
        return 'response from GET'


# run: {"controller": "SyncMetaController", "method": "options", "url": "/api/settings/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "SyncMetaController", "openapi_url": "/docs/openapi.json/"}  # noqa: E501, ERA001
