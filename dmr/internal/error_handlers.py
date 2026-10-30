from collections.abc import Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, final

from django.http import HttpRequest, HttpResponse
from django.utils.translation import get_language_from_path

from dmr.exceptions import NotAcceptableError
from dmr.internal.negotiation import negotiate_renderer
from dmr.internal.types import FormatError

if TYPE_CHECKING:
    from dmr.renderers import Renderer
    from dmr.serializer import BaseSerializer


def normalize_prefixes(prefix: str, *prefixes: str) -> tuple[str, ...]:
    """
    Normalize path prefixes to start with a leading slash.

    .. code-block:: python

        >>> normalize_prefixes('api/')
        ('/api/',)

        >>> normalize_prefixes('/api', '/rest/', 'json')
        ('/api/', '/rest/', '/json/')

    """
    all_prefixes = [prefix, *prefixes]
    return tuple(f'/{pref.strip("/")}/' for pref in all_prefixes)


def normalize_languages(
    languages: Sequence[str] | None,
) -> tuple[str, ...] | None:
    """
    Make languages lower case, so they can be compared with the path.

    .. code-block:: python

        >>> normalize_languages(['en', 'RU-ru'])
        ('en', 'ru-ru')

        >>> normalize_languages(None) is None
        True

    """
    if languages is None:
        return None
    return tuple(language.lower() for language in languages)


def has_path_prefix(
    request: HttpRequest,
    prefixes: tuple[str, ...],
    languages: tuple[str, ...] | None,
) -> bool:
    """
    Tell whether the request path starts with one of the prefixes.

    With ``i18n_patterns`` the path starts with a language,
    like ``/en/api/missing/``. When the path does not match as it is,
    we cut that language and check the rest of the path again.

    When ``languages`` is ``None``, any language that Django knows is cut.
    Otherwise, only the languages from the list are cut.
    They must be written in the path exactly, ``en`` does not match ``en-gb``.
    """
    path = request.path
    if path.startswith(prefixes):
        return True
    language, _, path_after_language = path[1:].partition('/')
    if languages is None:
        if get_language_from_path(path) is None:
            return False
    elif language.lower() not in languages:
        return False
    return f'/{path_after_language}'.startswith(prefixes)


@final
class NegotiatedErrorRenderer:
    """
    Render an error payload with content negotiation.

    It picks a renderer by the request's ``Accept`` header.
    When ``Accept`` cannot be satisfied,
    it renders :exc:`~dmr.exceptions.NotAcceptableError`
    with the first configured renderer instead.
    """

    __slots__ = ('_format_error', '_renderers', '_resolved', '_serializer')

    def __init__(
        self,
        *,
        serializer: type['BaseSerializer'],
        format_error: FormatError,
        renderers: Sequence['Renderer'] | None,
    ) -> None:
        """Store the handler configuration, renderers are resolved later."""
        self._serializer = serializer
        self._format_error = format_error
        self._renderers = renderers
        self._resolved: tuple[dict[str, Renderer], Renderer] | None = None

    def __call__(
        self,
        request: HttpRequest,
        *,
        raw_data: Any,
        status_code: HTTPStatus,
    ) -> HttpResponse:
        """Render *raw_data* with a renderer negotiated for *request*."""
        from dmr.response import build_response  # noqa: PLC0415

        renderers_by_type, default_renderer = self._resolve_renderers()
        try:
            renderer = negotiate_renderer(
                request,
                renderers_by_type,
                default=default_renderer,
            )
        except NotAcceptableError as exc:
            return build_response(
                serializer=self._serializer,
                raw_data=self._format_error(exc),
                status_code=exc.status_code,
                renderer=default_renderer,
            )

        return build_response(
            serializer=self._serializer,
            raw_data=raw_data,
            status_code=status_code,
            renderer=renderer,
        )

    def _resolve_renderers(self) -> tuple[dict[str, 'Renderer'], 'Renderer']:
        if self._resolved is None:
            from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

            renderers = (
                resolve_setting(Settings.renderers)
                if self._renderers is None
                else self._renderers
            )
            renderers_by_type = {
                renderer.content_type: renderer
                for renderer in renderers
                if not renderer.streaming
            }
            self._resolved = (
                renderers_by_type,
                next(iter(renderers_by_type.values())),
            )
        return self._resolved
