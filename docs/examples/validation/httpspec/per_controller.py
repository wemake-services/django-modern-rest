from http import HTTPStatus

from django_modern_rest import Controller, modify
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.settings import HttpSpec


class JobController(Controller[PydanticSerializer]):
    no_validate_http_spec = frozenset((HttpSpec.empty_response_body,))

    @modify(status_code=HTTPStatus.NO_CONTENT)
    def post(self) -> int:
        job_id = 4  # very random number :)
        return job_id  # noqa: RET504


# run: {"controller": "JobController", "method": "post", "url": "/api/job/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
