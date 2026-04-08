from collections.abc import Mapping
from http import HTTPStatus
from typing import Annotated, Any, ClassVar, Final

from typing_extensions import TypedDict

from dmr.controller import Controller
from dmr.cookies import NewCookie
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.negotiation import ContentType, accepts, conditional_type
from dmr.response import APIError
from dmr.serializer import BaseSerializer

_PROBLEM_DETAILS_FIELDS: Final = frozenset((
    'detail',
    'type',
    'title',
    'instance',
    'status',
))


class ProblemDetailsModel(TypedDict, total=False):
    """
    Error payload model for Problem Details.

    See https://datatracker.ietf.org/doc/html/rfc9457
    for the detailed description of each field.
    """

    detail: str
    status: int
    type: str
    title: str
    instance: str


class ProblemDetailsError(APIError[ProblemDetailsModel]):
    """
    Problem Details exception.

    It is a subclass of :class:`dmr.response.APIError`,
    so you can raise it anywhere in the REST part of your app.

    There are two major use-cases that we support for this class:

    1. Direct usage: you raise an error and get what you raise, no changes
    2. Conditional usage: you call ``conditional_error`` method
       and if the client accepts ``application/problem+json``, we will return
       the proper Problem Details description. But, if it is not requested
       directly, we will return our regular :class:`dmr.errors.ErrorModel`

    Both use-cases are independent. You can decide what to use per controller.
    """

    content_type: ClassVar[str] = ContentType.json_problem_details

    def __init__(
        self,
        # Problem details fields:
        detail: str,
        *,
        status_code: HTTPStatus,
        type: str | None = None,  # noqa: A002
        title: str | None = None,
        instance: str | None = None,
        extra: Mapping[str, Any] | None = None,
        # Response:
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        # Logic:
        show_status: bool = True,
        show_detail: bool = True,
    ) -> None:
        """
        Create Problem Details exception.

        Parameters:
            detail: detail field of the problem details protocols.
            status_code: status code field of the problem details protocols.
            title: title field of the problem details protocols.
            instance: instance field of the problem details protocols.
            extra: extra fields to be added to the final payload.
                Cannot shadow the original fields.
            headers: Headers to add to the response.
            cookies: Cookies to add the the response.
            show_status: Should we include the status field to the end payload?
            show_detail: Should we include the detail field to the end payload?

        Note that *detail* and *status_code* are required fields
        due to technical reasons, but you can disable them in the output
        via *show_status* and *show_detail*
        if you don't need them for some reason.
        """
        self.detail = detail
        self.status_code = status_code
        self.type = type
        self.title = title
        self.instance = instance
        self.extra = extra
        self._show_status = show_status
        self._show_detail = show_detail

        # Part of the `APIError`:
        super().__init__(
            self._error_details(),
            status_code=status_code,
            headers=headers,
            cookies=cookies,
        )

    @classmethod
    def conditional_error(
        cls,
        detail: str,
        *,
        status_code: HTTPStatus,
        controller: Controller[BaseSerializer],
        # Optional fields:
        type: str | None = None,  # noqa: A002
        title: str | None = None,
        instance: str | None = None,
        extra: Mapping[str, Any] | None = None,
        # Response:
        headers: Mapping[str, str] | None = None,
        cookies: Mapping[str, NewCookie] | None = None,
        # Logic:
        show_status: bool = True,
        show_detail: bool = True,
    ) -> APIError[Any]:
        """
        Create conditional error.

        If request accepts ``application/problem+json`` then return
        a Problem Details exception. If not, return regular
        :class:`dmr.response.APIError` instance.

        Otherwise, returns regular error from *controller* using its
        :meth:`~dmr.controller.Controller.format_error` method for formatting.
        """
        if accepts(controller.request, cls.content_type):
            return cls(
                detail=detail,
                status_code=status_code,
                type=type,
                title=title,
                instance=instance,
                extra=extra,
                headers=headers,
                cookies=cookies,
                show_status=show_status,
                show_detail=show_detail,
            )
        return APIError(
            controller.format_error(detail, error_type=type),
            status_code=status_code,
            headers=headers,
            cookies=cookies,
        )

    @classmethod
    def error_model(
        cls,
        existing_errors: Mapping[str, Any],
        content_type: str | None = None,
    ) -> Any:
        """
        Builds an error model for conditional responses.

        Only use this method when you use ``conditional_error``.
        If you are using regular exceptions,
        use ``ProblemDetailsModel`` directly.
        """
        return Annotated[
            *(ProblemDetailsModel, *existing_errors.values()),  # pyrefly: ignore[not-a-type]
            conditional_type({
                (
                    content_type or ContentType.json_problem_details
                ): ProblemDetailsModel,
                **existing_errors,
            }),
        ]

    # TODO: make an overload maybe?
    @classmethod
    def format_error(
        cls,
        error: str | Exception,
        *,
        loc: str | list[str | int] | None = None,
        error_type: str | ErrorType | None = None,
        status_code: HTTPStatus | None = None,
        title: str | None = None,
        instance: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ErrorModel | ProblemDetailsModel:
        """Format other errors to be in format of Problem Details."""
        default_format = format_error(error, loc=loc, error_type=error_type)
        status_code = status_code or getattr(error, 'status_code', None)
        show_status = status_code is not None
        return cls(
            '; '.join(msg['msg'] for msg in default_format['detail']),
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
            status_code=status_code or HTTPStatus.INTERNAL_SERVER_ERROR,
            show_status=show_status,
        ).raw_data

    def _error_details(self) -> ProblemDetailsModel:  # noqa: C901
        if self.extra:
            common = _PROBLEM_DETAILS_FIELDS.intersection(
                self.extra.keys(),
            )
            if common:
                raise ValueError(
                    f'Field "extra" cannot contain {common!r} fields',
                )

        problem_details: ProblemDetailsModel = {}
        if self._show_detail:
            problem_details['detail'] = self.detail
        if self._show_status:
            problem_details['status'] = int(self.status_code)

        if self.type is not None:
            problem_details['type'] = self.type
        if self.title is not None:
            problem_details['title'] = self.title
        if self.instance is not None:
            problem_details['instance'] = self.instance
        if self.extra is not None:
            problem_details.update(self.extra)  # type: ignore[typeddict-item]
        return problem_details
