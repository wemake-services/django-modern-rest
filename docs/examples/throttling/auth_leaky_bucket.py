from dmr import Controller
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.throttling import Rate, SyncThrottle
from dmr.throttling.algorithms import LeakyBucket


class LoginController(Controller[PydanticFastSerializer]):
    throttling = (
        SyncThrottle(
            max_requests=5,
            duration_in_seconds=Rate.minute,
            algorithm=LeakyBucket(),
        ),
    )

    def post(self) -> str:
        return 'logged in'
