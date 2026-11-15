from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.throttling import Rate, SyncThrottle


class SyncController(Controller[PydanticFastSerializer]):
    @modify(
        throttling=[SyncThrottle(1, Rate.minute)],
        x_extensions={'x-rate-limit': ['1/m per IP']},
    )
    def get(self) -> str:
        return 'inside'


# openapi: {"controller": "SyncController", "openapi_url": "/docs/openapi.json"}  # noqa: ERA001
