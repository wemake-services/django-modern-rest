from http import HTTPStatus

from dirty_equals import IsStr
from inline_snapshot import snapshot

from django_modern_rest import (
    Blueprint,
    Body,
    Controller,
    ResponseSpec,
    modify,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer


class _Blueprint(Blueprint[PydanticSerializer]):
    responses = [
        ResponseSpec(float, status_code=HTTPStatus.RESET_CONTENT),
    ]

    @modify(
        extra_responses=[ResponseSpec(bool, status_code=HTTPStatus.CREATED)],
    )
    def put(self) -> str:
        raise NotImplementedError


class _Controller(Controller[PydanticSerializer]):
    responses = [
        ResponseSpec(int, status_code=HTTPStatus.ACCEPTED),
    ]
    blueprints = [_Blueprint]

    @modify(
        extra_responses=[
            ResponseSpec(
                complex,
                status_code=HTTPStatus.NON_AUTHORITATIVE_INFORMATION,
            ),
        ],
    )
    def get(self) -> str:
        raise NotImplementedError


def test_collected_responses() -> None:
    """Ensure that responses are corrected correctly."""
    assert _Controller.api_endpoints['PUT'].metadata.responses == snapshot({
        HTTPStatus.OK: ResponseSpec(return_type=str, status_code=HTTPStatus.OK),
        HTTPStatus.CREATED: ResponseSpec(
            return_type=bool,
            status_code=HTTPStatus.CREATED,
        ),
        HTTPStatus.RESET_CONTENT: ResponseSpec(
            return_type=float,
            status_code=HTTPStatus.RESET_CONTENT,
        ),
        HTTPStatus.ACCEPTED: ResponseSpec(
            return_type=int,
            status_code=HTTPStatus.ACCEPTED,
        ),
        HTTPStatus.NOT_ACCEPTABLE: ResponseSpec(
            return_type=_Controller.error_model,
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            description=IsStr(),  # type: ignore[arg-type]
        ),
        HTTPStatus.UNPROCESSABLE_ENTITY: ResponseSpec(
            return_type=_ControllerWithParsing.error_model,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            description=IsStr(),  # type: ignore[arg-type]
        ),
    })
    assert _Controller.api_endpoints['GET'].metadata.responses == snapshot({
        HTTPStatus.OK: ResponseSpec(return_type=str, status_code=HTTPStatus.OK),
        HTTPStatus.NON_AUTHORITATIVE_INFORMATION: ResponseSpec(
            return_type=complex,
            status_code=HTTPStatus.NON_AUTHORITATIVE_INFORMATION,
        ),
        HTTPStatus.ACCEPTED: ResponseSpec(
            return_type=int,
            status_code=HTTPStatus.ACCEPTED,
        ),
        HTTPStatus.NOT_ACCEPTABLE: ResponseSpec(
            return_type=_Controller.error_model,
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            description=IsStr(),  # type: ignore[arg-type]
        ),
        HTTPStatus.UNPROCESSABLE_ENTITY: ResponseSpec(
            return_type=_ControllerWithParsing.error_model,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            description=IsStr(),  # type: ignore[arg-type]
        ),
    })


class _ControllerWithParsing(
    Controller[PydanticSerializer],
    Body[dict[str, str]],
):
    def post(self) -> str:
        raise NotImplementedError


def test_collected_responses_with_parsing() -> None:
    """Ensures that component parsers add correct metadata."""
    assert _ControllerWithParsing.api_endpoints[
        'POST'
    ].metadata.responses == snapshot({
        HTTPStatus.CREATED: ResponseSpec(
            return_type=str,
            status_code=HTTPStatus.CREATED,
        ),
        HTTPStatus.BAD_REQUEST: ResponseSpec(
            return_type=_ControllerWithParsing.error_model,
            status_code=HTTPStatus.BAD_REQUEST,
            description=IsStr(),  # type: ignore[arg-type]
        ),
        HTTPStatus.NOT_ACCEPTABLE: ResponseSpec(
            return_type=_ControllerWithParsing.error_model,
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            description=IsStr(),  # type: ignore[arg-type]
        ),
        HTTPStatus.UNPROCESSABLE_ENTITY: ResponseSpec(
            return_type=_ControllerWithParsing.error_model,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            description=IsStr(),  # type: ignore[arg-type]
        ),
    })


class _ControllerWithoutValidation(
    Controller[PydanticSerializer],
):
    validate_responses = False

    def post(self) -> str:
        raise NotImplementedError


def test_collected_responses_without_validation() -> None:
    """Ensures that response validation adds correct metadata."""
    assert _ControllerWithoutValidation.api_endpoints[
        'POST'
    ].metadata.responses == snapshot({
        HTTPStatus.CREATED: ResponseSpec(
            return_type=str,
            status_code=HTTPStatus.CREATED,
        ),
        HTTPStatus.NOT_ACCEPTABLE: ResponseSpec(
            return_type=_ControllerWithParsing.error_model,
            status_code=HTTPStatus.NOT_ACCEPTABLE,
            description=IsStr(),  # type: ignore[arg-type]
        ),
    })
