from dmr import Controller, ResponseSpec
from dmr.exceptions import NotAuthenticatedError
from dmr.plugins.pydantic import PydanticSerializer


class UsersController(Controller[PydanticSerializer]):
    responses = (
        ResponseSpec(
            Controller.error_model,
            status_code=NotAuthenticatedError.status_code,
        ),
    )

    def post(self) -> dict[str, str]:
        assert self.request.LANGUAGE_CODE == 'ru'
        raise NotAuthenticatedError  # demo for the custom error translation


# run: {"controller": "UsersController", "method": "post", "headers": {"Accept-Language": "ru"}, "url": "/api/lang/", "assert-error-text": "security", "fail-with-body": false}  # noqa: ERA001, E501
