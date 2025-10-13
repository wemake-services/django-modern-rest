from typing import Any, Final

from django.test import AsyncClient, AsyncRequestFactory, Client, RequestFactory
from typing_extensions import override


class _DMRMixin:
    _content_type: Final = 'application/json'

    @override
    def _base_environ(self, **request: Any) -> Any:  # type: ignore[misc]
        request['CONTENT_TYPE'] = self._content_type
        return super()._base_environ(  # type: ignore[misc]
            **request,
        )

    @override
    def _encode_json(  # type: ignore[misc]
        self,
        data: Any,  # noqa: WPS110
        content_type: str,
    ) -> Any:
        return super()._encode_json(  # type: ignore[misc]
            data,
            self._content_type,
        )

    @override
    def _encode_data(  # type: ignore[misc]
        self,
        data: Any,  # noqa: WPS110
        content_type: str,
    ) -> Any:
        return super()._encode_data(  # type: ignore[misc]
            data,
            self._content_type,
        )


class DMRRequestFactory(_DMRMixin, RequestFactory):
    """
    Test utility for testing apps using ``django_modern_rest``.

    Based on :class:`django.test.RequestFactory`.
    See their docs for advanced usage:
    https://docs.djangoproject.com/en/dev/topics/testing/tools

    This type, in contrast to a regular ``RequestFactory``,
    sets ``content-type`` as ``application/json``.

    Sets WSGI environment.
    """


class DMRAsyncRequestFactory(_DMRMixin, AsyncRequestFactory):
    """
    Version of :class:`DMRRequestFactory` but for ASGI enviroment.

    Uses the exactly the same API.
    """


class DMRClient(_DMRMixin, Client):
    """
    Test utility for testing apps using ``django_modern_rest``.

    Based on :class:`django.test.Client`.
    See their docs for advanced usage:
    https://docs.djangoproject.com/en/dev/topics/testing/tools

    This type, in contrast to a regular ``Client``,
    sets ``content-type`` as ``application/json``.
    """

    # TODO: add `csrf` support


class DMRAsyncClient(_DMRMixin, AsyncClient):
    """
    Async version of :class:`DMRClient`.

    Uses ``async`` API.
    Requires you to ``await`` calls to ``.get``, ``.post``, etc.
    """
