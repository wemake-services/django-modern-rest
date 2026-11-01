import dataclasses
from abc import abstractmethod
from collections.abc import Mapping, Sequence, Set
from http import HTTPMethod, HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Protocol

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from typing_extensions import TypeForm, override

from dmr.errors import ErrorModel, format_error
from dmr.internal.csrf import csrf_header_name, ensure_csrf
from dmr.internal.error_handlers import (
    NegotiatedErrorRenderer,
    has_path_prefix,
    normalize_languages,
    normalize_prefixes,
)
from dmr.internal.types import FormatError, StrOrPromise
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider
from dmr.openapi.objects import Reference, SecurityRequirement, SecurityScheme
from dmr.security.base import unauth_response_spec
from dmr.semantic_schema import SecurityProvider, SecurityRequirementMerger

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.renderers import Renderer
    from dmr.serializer import BaseSerializer


_CSRF_FAILED_WITH_REASON_MSG: Final = _('CSRF Failed: {reason}')
_CSRF_FAILED_MSG: Final = _('CSRF Failed.')

#: Matches Django's definition in `CsrfViewMiddleware`.
SAFE_HTTP_METHODS: Final = frozenset((
    HTTPMethod.GET,
    HTTPMethod.HEAD,
    HTTPMethod.OPTIONS,
    HTTPMethod.TRACE,
))

#: Default security scheme name for CSRF.
CSRF_SCHEME_NAME: Final = 'csrf'

#: Default security scheme name for the CSRF header (cookie mode only).
CSRF_HEADER_SCHEME_NAME: Final = 'csrf_header'


def csrf_security_scheme(
    scheme_name: str,
    header_scheme_name: str,
) -> dict[str, SecurityScheme | Reference]:
    """
    Build the security scheme that describes where the CSRF secret is stored.

    By default Django keeps the CSRF secret in the
    ``CSRF_COOKIE_NAME`` cookie, so the scheme is an ``apiKey`` in ``cookie``.

    With ``CSRF_USE_SESSIONS = True`` Django requires to send CSRF in a header
    (``CSRF_HEADER_NAME``). In that mode there is no separate cookie scheme;
    the header alone is the complete requirement.

    Args:
        scheme_name: Security scheme name that we use for the CSRF token secret.
        header_scheme_name: Security scheme name
            that we use for the CSRF token value.

    .. versionadded:: 0.16.0
    .. versionchanged:: 0.17.0
        Now this function returns a :class:`dict` object of schemes.
        And accepts the names for these schemes.
        Now when ``CSRF_USE_SESSIONS`` is defined,
        we return the header security scheme.

    """
    if settings.CSRF_USE_SESSIONS:
        return {
            header_scheme_name: SecurityScheme(
                type='apiKey',
                name=csrf_header_name(),
                security_scheme_in='header',
                description=(
                    'CSRF protection, the secret is stored in the session'
                ),
            ),
        }

    return {
        scheme_name: SecurityScheme(
            type='apiKey',
            name=settings.CSRF_COOKIE_NAME,
            security_scheme_in='cookie',
            description='CSRF protection, the secret is stored in the cookie',
        ),
        header_scheme_name: SecurityScheme(
            type='apiKey',
            name=csrf_header_name(),
            security_scheme_in='header',
            description='CSRF protection, the token value in the header',
        ),
    }


class CSRFAuthMixin(ResponseSpecProvider, SecurityProvider):  # noqa: WPS214
    """
    Shared parts of auth classes that are protected by CSRF.

    This mixin does all of it. Subclasses only have to:

    - set ``security_scheme_name``, ``csrf_scheme_name``, and
      ``csrf_header_scheme_name`` attributes,
    - implement :meth:`auth_security_scheme` with their own scheme,
    - call ``_ensure_csrf`` from ``__call__`` at the right moment.

    Must be listed before the concrete auth base in the class bases,
    so the methods here win over the default ones.

    .. versionadded:: 0.16.0
    """

    __slots__ = ()

    security_scheme_name: str
    csrf_scheme_name: str
    csrf_header_scheme_name: str

    @property
    def www_authenticate_challenge(self) -> str | None:
        """
        This auth has no challenge to advertise, so this returns ``None``.

        A challenge asks the client for the ``Authorization`` header,
        while this auth reads credentials that need CSRF protection instead.
        """

    @abstractmethod
    def auth_security_scheme(self) -> SecurityScheme:
        """Provides the security scheme of the auth itself, without CSRF."""
        raise NotImplementedError

    def csrf_security_scheme(self) -> dict[str, SecurityScheme | Reference]:
        """
        Provides the security scheme for CSRF cookie/session storage.

        .. versionchanged:: 0.17.0
            Now this method returns a :class:`dict` object of schemes.
            Now when ``CSRF_USE_SESSIONS`` is defined,
            we return the header security scheme.

        """
        return csrf_security_scheme(
            scheme_name=self.csrf_scheme_name,
            header_scheme_name=self.csrf_header_scheme_name,
        )

    @override
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> dict[str, 'SecurityScheme | Reference']:
        """Provides the auth security scheme together with the CSRF one(s)."""
        return {
            **self.csrf_security_scheme(),
            self.security_scheme_name: self.auth_security_scheme(),
        }

    @override
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[SecurityRequirement]:
        """Requires the auth scheme and CSRF for unsafe HTTP methods."""
        requirement: SecurityRequirement = {self.security_scheme_name: []}
        # CSRF is not required for safe http methods:
        if not self._is_safe_http_method(metadata):
            requirement[self.csrf_header_scheme_name] = []
            # When CSRF is sent via sessions, we only need the header scheme:
            if not settings.CSRF_USE_SESSIONS:
                requirement[self.csrf_scheme_name] = []
        return [requirement]

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Declares extra responses for failed auth and failed CSRF checks."""
        auth_response = self._add_new_response(
            unauth_response_spec(controller_cls, metadata),
            existing_responses,
        )
        if self._is_safe_http_method(metadata):
            # CSRF errors can't happen for safe methods:
            return auth_response
        return [
            *auth_response,
            *self._add_new_response(
                csrf_response_spec(return_type=controller_cls.error_model),
                existing_responses,
            ),
        ]

    def _ensure_csrf(self, controller: 'Controller[BaseSerializer]') -> None:
        """
        Enforce the CSRF check, raise ``APIError`` (403) if it fails.

        Override this to skip the check when the request carries
        no credentials for this auth at all, so the auth chain
        can fall through to the next auth without a CSRF error.
        """
        ensure_csrf(controller)

    def _is_safe_http_method(self, metadata: EndpointMetadata) -> bool:
        return metadata.method.upper() in SAFE_HTTP_METHODS


def csrf_message(reason: str) -> str:
    """
    Return CSRF failure message according the security rules.

    .. versionadded:: 0.16.0
    """
    from django.conf import settings  # noqa: PLC0415

    if reason and settings.DEBUG:
        return _CSRF_FAILED_WITH_REASON_MSG.format(reason=reason)  # type: ignore[no-any-return]

    return force_str(_CSRF_FAILED_MSG)


class _CSRFViewProtocol(Protocol):
    def __call__(
        self,
        request: HttpRequest,
        reason: str = '',
    ) -> HttpResponse: ...


def build_csrf_handler(  # noqa: WPS211
    prefix: str,
    /,
    *prefixes: str,
    serializer: type['BaseSerializer'],
    format_error: FormatError = format_error,
    renderers: Sequence['Renderer'] | None = None,
    status_code: HTTPStatus = HTTPStatus.FORBIDDEN,
    languages: Sequence[str] | None = None,
) -> _CSRFViewProtocol:
    """
    Create a CSRF error handler that returns a response with negotiation.

    Use this function to build ``CSRF_FAILURE_VIEW`` handler in ``settings.py``.

    All prefixes are normalized to start with a leading slash.
    If the request path matches any of them, a REST response is returned
    using the same serializer and renderers as your API.
    If the client's ``Accept`` does not match any renderer, the first
    configured renderer is used.
    For non-matching paths, Django's default ``CSRF_FAILURE_VIEW`` handler
    is used.

    Args:
        prefix: Path prefix (e.g. ``'api/'``) for which to return API responses.
        *prefixes: Additional path prefixes.
        format_error: Callable used to build the error body for the response.
        serializer: Serializer class used to serialize the error body.
        renderers: Optional sequence of renderers. If omitted, uses
            :attr:`~dmr.settings.Settings.renderers` from settings.
        status_code: Status code to be returned. Defaults to ``403``.
        languages: Optional languages that can start the path, like
            ``('en', 'ru')`` for ``i18n_patterns``. Only these languages
            are allowed and they must match the path exactly,
            so ``en`` does not match ``/en-gb/api/``.
            If omitted, all languages of Django are allowed.

    See also:
        https://docs.djangoproject.com/en/6.1/ref/settings/#csrf-failure-view

    .. versionadded:: 0.16.0

    .. versionchanged:: 0.17.0
        Added ``languages`` argument.
    """
    all_prefixes = normalize_prefixes(prefix, *prefixes)
    all_languages = normalize_languages(languages)
    render_error = NegotiatedErrorRenderer(
        serializer=serializer,
        format_error=format_error,
        renderers=renderers,
    )

    def factory(request: HttpRequest, reason: str = '') -> HttpResponse:
        from django.views.csrf import csrf_failure  # noqa: PLC0415

        if not has_path_prefix(request, all_prefixes, all_languages):
            return csrf_failure(request, reason)
        return render_error(
            request,
            raw_data=format_error(csrf_message(reason)),
            status_code=status_code,
        )

    return factory


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class CSRFSemanticSchemaProvider(
    ResponseSpecProvider,
    SecurityProvider,
    SecurityRequirementMerger,
):
    """
    Provide response specs for controllers that have ``csrf_exempt = False``.

    Only provides response specs for controllers that set explicit
    ``csrf_exempt = False`` setting and define non-safe HTTP endpoints,
    like ``post`` or ``put``.

    Should be added to :data:`dmr.settings.Settings.semantic_schema_providers`
    setting.

    Attributes:
        error_model: Error model to be returned. Since CSRF is executed
            in a middleware before any controller, we can't get the error
            model from a controller. This is why this has
            to be configured separately.
        status_code: Status code that should be set for failed CSRF responses.
        description: Human readable description, what the response is for.
        security_scheme_name: Security scheme name for the CSRF cookie/session
            storage scheme.
        csrf_header_scheme_name: Security scheme name for the CSRF header
            scheme (cookie mode only, i.e. ``CSRF_USE_SESSIONS = False``).
        safe_http_methods: Set of secure HTTP method names.

    .. warning::

        We can't possibly detect if CSRF enabled for any controller or not.
        There can be custom middleware, decorators like ``@csrf_protect``,
        or even ``ensure_csrf()`` inline calls.

        So, if you know that CSRF is disabled and still want
        to use ``csrf_exempt = False`` for some reason (?),
        disable this provider from settings.

    .. versionadded:: 0.16.0
    """

    # Instance API:
    error_model: TypeForm[Any] = ErrorModel
    status_code: HTTPStatus | None = None
    description: StrOrPromise | None = None
    security_scheme_name: str = CSRF_SCHEME_NAME
    security_header_scheme_name: str = CSRF_HEADER_SCHEME_NAME
    safe_http_methods: Set[HTTPMethod] = SAFE_HTTP_METHODS

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Returns response specs for CSRF endpoints."""
        if self._is_csrf_disabled(metadata, controller_cls):
            return []

        return self._add_new_response(
            csrf_response_spec(
                # We can't use `controller_cls` here, because
                # the error will be returned not from a controller,
                # but from a `CSRF_FAILURE_VIEW` view.
                # So, to customize this, you would need to customize
                # two things: `format_error` in `build_csrf_handler`
                # and `error_model` parameter to `CSRFSemanticSchemaProvider`
                # in `semantic_schema_providers`.
                return_type=self.error_model,
                status_code=self.status_code,
                description=self.description,
            ),
            existing_responses,
        )

    @override
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> dict[str, SecurityScheme | Reference]:
        """Provides a security schema definition."""
        if self._is_csrf_disabled(metadata, controller_cls):
            return {}
        return csrf_security_scheme(
            scheme_name=self.security_scheme_name,
            header_scheme_name=self.security_header_scheme_name,
        )

    @override
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list[SecurityRequirement]:
        """Provides a security schema usage requirement."""
        if self._is_csrf_disabled(metadata, controller_cls):
            return []
        requirement: SecurityRequirement = {
            self.security_header_scheme_name: [],
        }
        # When CSRF is sent via sessions, we only need the header scheme:
        if not settings.CSRF_USE_SESSIONS:
            requirement[self.security_scheme_name] = []
        return [requirement]

    @override
    def merge_security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        own_requirements: list[SecurityRequirement],
        auth_requirements: list[SecurityRequirement],
    ) -> list[SecurityRequirement]:
        """Joins CSRF requirement with each auth requirement."""
        # We join the security requirements with `AND` logic for this type.
        # It needs both auth and CSRF checks to pass to be able to login.
        if not own_requirements:
            return auth_requirements
        if not auth_requirements:
            return own_requirements
        return [
            {**auth, **own}
            for own in own_requirements
            for auth in auth_requirements
        ]

    def _is_csrf_disabled(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> bool:
        return (
            controller_cls.csrf_exempt
            or metadata.method.upper() in self.safe_http_methods
        )


def csrf_response_spec(
    *,
    return_type: TypeForm[Any],
    status_code: HTTPStatus | None = None,
    description: StrOrPromise | None = None,
) -> ResponseSpec:
    """
    Response spec for CSRF error.

    .. versionadded:: 0.16.0
    """
    return ResponseSpec(
        return_type=return_type,
        status_code=(
            HTTPStatus.FORBIDDEN if status_code is None else status_code
        ),
        description=(
            'Raised when CSRF check failed'
            if description is None
            else description
        ),
    )
