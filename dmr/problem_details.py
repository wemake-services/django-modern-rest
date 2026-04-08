from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated, Any, TypeVar

from django.http import HttpResponse
from typing_extensions import TypedDict

from dmr.negotiation import ContentType
from dmr.response import APIError

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.cookies import NewCookie
    from dmr.renderers import Renderer
    from dmr.serializer import BaseSerializer


class ProblemDetailsModel(TypedDict, total=False):
    detail: str
    type: str | None
    title: str | None
    instance: str | None


_ErrorModelT = TypeVar('_ErrorModelT')


class ProblemDetailsError(Exception):
    def __init__(
        self,
        *,
        # Required data:
        detail: str,
        status_code: HTTPStatus,
        # Promblem details fields:
        type: str | None = None,  # noqa: A002
        title: str | None = None,
        instance: str | None = None,
        extra: Mapping[str, Any] | None = None,
        # Response:
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, 'NewCookie'] | None = None,
        renderer: 'Renderer | None' = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.type = type
        self.title = title
        self.instance = instance
        self.extra = extra
        self.headers = headers
        self.cookies = cookies
        self.renderer = renderer

    def to_error(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> HttpResponse:
        return controller.to_error(
            self.error_details(),
            status_code=self.status_code,
            headers=self.headers,
            cookies=self.cookies,
            renderer=self.renderer,
        )

    def error_details(self) -> ProblemDetailsModel:
        problem_details: ProblemDetailsModel = {'details': self.detail}
        if self.type is not None:
            problem_details['type'] = self.type
        if self.title is not None:
            problem_details['title'] = self.title
        if self.instance is not None:
            problem_details['instance'] = self.instance
        if self.extra is not None:
            problem_details.update(self.extra)
        return problem_details

    @classmethod
    def build_error_model(
        cls,
        existing_errors: Mapping[str, Any],
        content_type: str | None = None,
    ) -> Any:
        from dmr.negotiation import ContentType, conditional_type

        return Annotated[
            *(ProblemDetailsModel, *existing_errors.values()),
            conditional_type({
                content_type
                or ContentType.json_problem_details: ProblemDetailsModel,
                **existing_errors,
            }),
        ]


_ErrorT = TypeVar('_ErrorT', bound=APIError)


def conditional_error(
    controller: 'Controller[BaseSerializer]',
    # Required data:
    detail: str,
    *,
    status_code: HTTPStatus,
    # Promblem details fields:
    type: str | None = None,  # noqa: A002
    title: str | None = None,
    instance: str | None = None,
    extra: Mapping[str, Any] | None = None,
    # Response:
    headers: Mapping[str, str] | None = None,
    cookies: Mapping[str, 'NewCookie'] | None = None,
    renderer: 'Renderer | None' = None,
    api_error_cls: type[_ErrorT] = APIError,
) -> _ErrorT | ProblemDetailsError:
    if controller.request.accepts(ContentType.json):
        return api_error_cls(controller.format_error(detail))
    return ProblemDetailsError(
        detail=detail,
        status_code=HTTPStatus.PAYMENT_REQUIRED,
        type='https://example.com/probs/out-of-credit',
        title='Not enough funds',
        instance='/account/users/1/',
        extra={'balance': 10, 'price': 15},
        headers=headers,
        cookies=cookies,
        renderer=renderer,
    )


def format_error(
    error: str | Exception,
    *,
    loc: str | list[str | int] | None = None,
    error_type: str | ErrorType | None = None,
) -> Any: ...
