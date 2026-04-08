from collections.abc import Mapping
from http import HTTPStatus
from typing import Annotated, Any, ClassVar, Final, Self, TypeVar

from django.http import HttpResponse
from typing_extensions import TypedDict

from dmr.controller import Controller
from dmr.cookies import NewCookie
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.negotiation import ContentType, conditional_type
from dmr.renderers import Renderer
from dmr.response import APIError
from dmr.serializer import BaseSerializer

_PROBLEM_DETAILS_FIELDS: Final = frozenset((
    'detail',
    'type',
    'title',
    'instance',
))


class ProblemDetailsModel(TypedDict, total=False):
    detail: str
    type: str | None
    title: str | None
    instance: str | None


_ErrorModelT = TypeVar('_ErrorModelT')


class ProblemDetailsError(Exception):
    content_type: ClassVar[str] = ContentType.json_problem_details

    def __init__(
        self,
        *,
        # Required data:
        detail: str,
        status_code: HTTPStatus,
        # Problem details fields:
        type: str | None = None,  # noqa: A002
        title: str | None = None,
        instance: str | None = None,
        extra: Mapping[str, Any] | None = None,
        # Response:
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        renderer: Renderer | None = None,
    ) -> None:
        if extra:
            common = _PROBLEM_DETAILS_FIELDS.intersection(
                extra.keys(),
            )
            if common:
                raise ValueError(
                    f'Field "extra" cannot contain {common!r} fields',
                )

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
        controller: Controller[BaseSerializer],
    ) -> HttpResponse:
        return controller.to_error(
            self.error_details(),
            status_code=self.status_code,
            headers=self.headers,
            cookies=self.cookies,
            renderer=self.renderer,
        )

    def error_details(self) -> ProblemDetailsModel:
        problem_details: ProblemDetailsModel = {'detail': self.detail}
        if self.type is not None:
            problem_details['type'] = self.type
        if self.title is not None:
            problem_details['title'] = self.title
        if self.instance is not None:
            problem_details['instance'] = self.instance
        if self.extra is not None:
            problem_details.update(self.extra)  # type: ignore[typeddict-item]
        return problem_details

    @classmethod
    def build_error_model(
        cls,
        existing_errors: Mapping[str, Any],
        content_type: str | None = None,
    ) -> Any:
        return Annotated[
            *(ProblemDetailsModel, *existing_errors.values()),
            conditional_type({
                (
                    content_type or ContentType.json_problem_details
                ): ProblemDetailsModel,
                **existing_errors,
            }),
        ]

    # TODO: make an overload maybe?
    @classmethod
    def build_error(
        cls,
        # Required data:
        detail: str,
        *,
        status_code: HTTPStatus,
        # Problem details fields:
        type: str | None = None,  # noqa: A002
        title: str | None = None,
        instance: str | None = None,
        extra: Mapping[str, Any] | None = None,
        # Response:
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        renderer: Renderer | None = None,
        # Infra:
        api_error_cls: type[APIError] = APIError,
        controller: Controller[BaseSerializer] | None = None,
    ) -> APIError | Self:
        if controller is None or controller.request.accepts(cls.content_type):
            return cls(
                detail=detail,
                status_code=status_code,
                type=type,
                title=title,
                instance=instance,
                extra=extra,
                headers=headers,
                cookies=cookies,
                renderer=renderer,
            )
        return api_error_cls(
            controller.format_error(detail),
            status_code=status_code,
            headers=headers,
            cookies=cookies,
        )

    # TODO: make an overload maybe?
    @classmethod
    def format_error(
        cls,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
        title: str | None = None,
        instance: str | None = None,
        extra: Mapping[str, Any] | None = None,
        # Infra:
        controller: Controller[BaseSerializer] | None = None,
    ) -> ErrorModel | ProblemDetailsModel:
        default_format = format_error(error, loc=loc, error_type=error_type)
        if controller is None or controller.request.accepts(cls.content_type):
            return cls(
                detail='; '.join(
                    msg['msg'] for msg in default_format['detail']
                ),
                type=(
                    next(
                        (
                            msg_type
                            for msg in default_format['detail']
                            if (msg_type := msg.get('type'))
                        ),
                        None,
                    )
                    if error_type is None
                    else str(error_type)
                ),
                title=title,
                instance=instance,
                extra=extra,
                status_code=HTTPStatus.OK,  # whatever
            ).error_details()
        return default_format
