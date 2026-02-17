from http import HTTPStatus

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer


class JobController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.NO_CONTENT)
    def post(self) -> None:
        print('Job created')  # noqa: WPS421


# run: {"controller": "JobController", "method": "post", "url": "/api/job/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
