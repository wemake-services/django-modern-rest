import asyncio
import inspect
import threading
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, ClassVar

from django.http import HttpResponse, HttpResponseBase
from django.urls import URLPattern

from dmr.exceptions import (
    DataRenderingError,
    InternalServerError,
    NotAuthenticatedError,
    ResponseSchemaError,
    ValidationError,
)
from dmr.internal.context import SerializerContext as SerializerContext
from dmr.internal.endpoint import ModifyAnyCallable as ModifyAnyCallable
from dmr.internal.endpoint import ModifyAsyncCallable as ModifyAsyncCallable
from dmr.internal.endpoint import ModifySyncCallable as ModifySyncCallable
from dmr.internal.endpoint import ValidateAnyCallable as ValidateAnyCallable
from dmr.internal.endpoint import ValidateAsyncCallable as ValidateAsyncCallable
from dmr.internal.endpoint import ValidateSyncCallable as ValidateSyncCallable
from dmr.internal.endpoint import modify as modify
from dmr.internal.endpoint import request_endpoint as request_endpoint
from dmr.internal.endpoint import validate as validate
from dmr.metadata import EndpointMetadata, ResponseModification
from dmr.negotiation import RequestNegotiator, ResponseNegotiator
from dmr.openapi.objects import Operation
from dmr.response import APIError, RedirectTo
from dmr.security.base import AsyncAuth, SyncAuth
from dmr.serializer import BaseSerializer
from dmr.settings import Settings, resolve_setting
from dmr.throttling import AsyncThrottle, SyncThrottle
from dmr.validation import (
    EndpointMetadataBuilder,
    EndpointMetadataValidator,
    ResponseValidator,
)
from dmr.validation.payload import PayloadBuilder

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.routing import Router
    from dmr.validation.response import ValidatedModification


class Endpoint:  # noqa: WPS214
    """
    Represents the single API endpoint.

    Is built during the import time.
    In the runtime only does response validate, which can be disabled.
    """

    __slots__ = (
        '_async_lock',
        '_func',
        '_serializer_context',
        '_sync_lock',
        'is_async',
        'metadata',
        'request_negotiator',
        'response_negotiator',
        'response_validator',
    )

    # Instance API:
    _func: Callable[..., Any]

    # Class API:
    serializer_context_cls: ClassVar[type[SerializerContext]] = (
        SerializerContext
    )
    metadata_builder_cls: ClassVar[type[EndpointMetadataBuilder]] = (
        EndpointMetadataBuilder
    )
    metadata_validator_cls: ClassVar[type[EndpointMetadataValidator]] = (
        EndpointMetadataValidator
    )
    metadata_cls: ClassVar[type[EndpointMetadata]] = EndpointMetadata
    response_modification_cls: ClassVar[type[ResponseModification]] = (
        ResponseModification
    )
    request_negotiator_cls: ClassVar[type[RequestNegotiator]] = (
        RequestNegotiator
    )
    response_negotiator_cls: ClassVar[type[ResponseNegotiator]] = (
        ResponseNegotiator
    )
    response_validator_cls: ClassVar[type[ResponseValidator]] = (
        ResponseValidator
    )
    payload_builder_cls: ClassVar[type[PayloadBuilder]] = PayloadBuilder

    def __init__(
        self,
        func: Callable[..., Any],
        *,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        """
        Create an entrypoint.

        Args:
            func: Entrypoint handler. An actual function to be called.
            controller_cls: ``Controller`` class that this endpoint belongs to.

        .. danger::

            Endpoint object must **not** have any mutable instance state,
            because its instance is reused for all requests.
            It is fine to have common locks for throttling, because
            this way we guard cache concurrent access
            from different thread / coroutines.

        """
        type_annotations = controller_cls.annotations_context(func)
        self._serializer_context = self.serializer_context_cls(
            func,
            controller_cls,
            type_annotations,
        )
        # We need to add payloads to functions that don't have it,
        # since decorator is optional:
        payload = self.payload_builder_cls(func)(controller_cls)
        # We add metadata in two steps:
        # 1. We construct metadata with no responses yet.
        #    We only do basic validation at this point: structure, types, etc.
        #    No semantics validation / etc.
        # 2. When metadata is ready, we collect all the responses from all
        #    of the components that support it. Including custom ones.
        #    Then we enrich metadata with collected responses and use it.
        # Done!
        metadata = self.metadata_builder_cls(
            payload=payload,
            controller_cls=controller_cls,
            func=func,
            metadata_cls=self.metadata_cls,
            response_modification_cls=self.response_modification_cls,
            component_parsers=self._serializer_context.component_parsers,
            type_annotations=type_annotations,
        )()
        self.metadata_validator_cls(metadata=metadata)(
            func,
            payload=payload,
            controller_cls=controller_cls,
        )
        func.__metadata__ = metadata  # type: ignore[attr-defined]
        self.metadata = metadata
        self.request_negotiator = self.request_negotiator_cls(
            self.metadata,
            controller_cls.serializer,
        )
        self.response_negotiator = self.response_negotiator_cls(
            self.metadata,
            controller_cls.serializer,
            streaming=controller_cls.streaming,
        )

        # We need a func before any wrappers, but with metadata:
        self.response_validator = self.response_validator_cls(
            metadata,
            controller_cls.serializer,
        )
        # We can now run endpoint's optimization:
        controller_cls.serializer.optimizer.optimize_endpoint(metadata)

        # Locks:
        self._sync_lock = threading.Lock()
        self._async_lock = asyncio.Lock()

        # Now we can add wrappers:
        if inspect.iscoroutinefunction(func):
            self.is_async = True
            self._func = self._async_endpoint(func)
        else:
            self.is_async = False
            self._func = self._sync_endpoint(func)

    def __call__(
        self,
        controller: 'Controller[BaseSerializer]',
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponseBase:
        """Run the endpoint and return the response."""
        return self._func(  # type: ignore[no-any-return]
            controller,
            *args,
            **kwargs,
        )

    def handle_error(
        self,
        controller: 'Controller[BaseSerializer]',
        exc: Exception,
    ) -> HttpResponseBase:
        """
        Return error response if possible.

        Override this method to add custom error handling.
        """
        # NOTE: if you change something here,
        # also change in `handle_async_error`
        if self.metadata.error_handler is not None:
            try:
                # We validate this, no error possible in runtime:
                return self.metadata.error_handler(  # type: ignore[return-value]
                    self,
                    controller,
                    exc,
                )
            except Exception:  # noqa: S110
                # We don't use `suppress` here for speed.
                pass  # noqa: WPS420
        # Per-endpoint error handler didn't work.
        # Now, try the per-controller one.
        try:
            return controller.handle_error(
                self,
                controller,
                exc,
            )
        except Exception:
            # And the last option is to handle error globally:
            return self._global_error_handler(controller, exc)

    async def handle_async_error(
        self,
        controller: 'Controller[BaseSerializer]',
        exc: Exception,
    ) -> HttpResponse:
        """
        Return error response if possible.

        Override this method to add custom async error handling.
        """
        # NOTE: if you change something here, also change in `handle_error`
        if self.metadata.error_handler is not None:
            try:
                # We validate this, no error possible in runtime:
                return await self.metadata.error_handler(  # type: ignore[no-any-return, misc]
                    self,
                    controller,
                    exc,
                )
            except Exception:  # noqa: S110
                # We don't use `suppress` here for speed.
                pass  # noqa: WPS420
        # Per-endpoint error handler didn't work.
        # Now, try the per-controller one.
        try:
            return await controller.handle_async_error(
                self,
                controller,
                exc,
            )
        except Exception:
            # And the last option is to handle error globally:
            return self._global_error_handler(controller, exc)

    def get_schema(
        self,
        path: str,
        pattern: URLPattern,
        controller_name: str,
        serializer: type[BaseSerializer],
        context: 'OpenAPIContext',
        router: 'Router',
    ) -> Operation:
        """Build an OpenAPI Operation from an endpoint."""
        operation_id = self.get_operation_id(
            path,
            controller_name,
            serializer,
            context,
        )
        request_body, params_list = context.generators.component_parsers(
            operation_id,
            pattern,
            self.metadata,
            serializer,
        )

        router_metadata = router.metadata_for(path)
        tags = [
            *router_metadata.tags,
            *(self.metadata.tags or []),
        ]

        return Operation(
            tags=tags or None,
            summary=(
                None
                if self.metadata.summary is None
                else str(self.metadata.summary)
            ),
            description=(
                None
                if self.metadata.description is None
                else str(self.metadata.description)
            ),
            deprecated=self.metadata.deprecated or router_metadata.deprecated,
            security=context.generators.security_scheme(
                self.metadata.auth,
                serializer,
            ),
            external_docs=self.metadata.external_docs,
            servers=self.metadata.servers,
            callbacks=self.metadata.callbacks,
            operation_id=operation_id,
            request_body=request_body,
            responses=context.generators.response(self.metadata, serializer),
            parameters=params_list,
        )

    def get_operation_id(
        self,
        path: str,
        controller_name: str,
        serializer: type[BaseSerializer],
        context: 'OpenAPIContext',
    ) -> str:
        """Customize how OperationId is generated for the OpenAPI."""
        return context.generators.operation_id(
            path,
            controller_name,
            self.metadata,
            serializer,
        )

    def _async_endpoint(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., Awaitable[HttpResponseBase]]:
        # NOTE: if you change something here, also change in `_sync_endpoint`
        @wraps(func)
        async def decorator(
            controller: 'Controller[BaseSerializer]',
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponseBase:
            try:  # noqa: WPS229
                controller.request.__dmr_endpoint__ = self  # type: ignore[attr-defined]

                # Run checks:
                await self._run_async_checks(controller)

                # Parse request and return response.
                # NOTE: the parsed context is inlined on purpose,
                # it must not become a local variable of this frame,
                # because it can contain credentials that would leak
                # into error reports of any endpoint.
                func_result = await func(
                    controller,
                    **self._serializer_context(self, controller),
                )
            except (APIError, RedirectTo) as exc:
                func_result = controller.to_error(
                    exc.raw_data,
                    status_code=exc.status_code,
                    headers=exc.headers,
                    cookies=getattr(exc, 'cookies', None),
                    renderer=getattr(exc, 'renderer', None),
                )
            except Exception as exc:
                func_result = await self.handle_async_error(controller, exc)
            return self._make_http_response(controller, func_result)

        return decorator

    def _sync_endpoint(
        self,
        func: Callable[..., Any],
    ) -> Callable[..., HttpResponseBase]:
        # NOTE: if you change something here, also change in `_async_endpoint`
        @wraps(func)
        def decorator(
            controller: 'Controller[BaseSerializer]',
            *args: Any,
            **kwargs: Any,
        ) -> HttpResponseBase:
            try:  # noqa: WPS229
                controller.request.__dmr_endpoint__ = self  # type: ignore[attr-defined]

                # Run checks:
                self._run_checks(controller)

                # Parse request and return response.
                # NOTE: the parsed context is inlined on purpose,
                # it must not become a local variable of this frame,
                # because it can contain credentials that would leak
                # into error reports of any endpoint.
                func_result = func(
                    controller,
                    **self._serializer_context(self, controller),
                )
            except (APIError, RedirectTo) as exc:
                func_result = controller.to_error(
                    exc.raw_data,
                    status_code=exc.status_code,
                    headers=exc.headers,
                    cookies=getattr(exc, 'cookies', None),
                    renderer=getattr(exc, 'renderer', None),
                )
            except Exception as exc:
                func_result = self.handle_error(controller, exc)
            return self._make_http_response(controller, func_result)

        return decorator

    # Sync checks:

    def _run_checks(self, controller: 'Controller[BaseSerializer]') -> None:
        # First round of throttling:
        self._run_throttle_before(controller)
        # Negotiate response:
        self.response_negotiator(controller.request)
        # Auth:
        self._run_auth(controller)
        # Second round of throttling:
        self._run_throttle_after(controller)

    def _run_throttle_before(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        if self.metadata.throttling_before_auth is None:
            return
        for throttle in self.metadata.throttling_before_auth:
            assert isinstance(throttle, SyncThrottle)  # noqa: S101
            throttle(self, controller, self._sync_lock)

    def _run_auth(self, controller: 'Controller[BaseSerializer]') -> None:
        if self.metadata.auth is None:
            return
        for auth in self.metadata.auth:
            assert isinstance(auth, SyncAuth)  # noqa: S101
            authed_by = auth(self, controller)
            if authed_by is not None:
                controller.request.__dmr_auth__ = authed_by  # type: ignore[attr-defined]
                return
        raise NotAuthenticatedError

    def _run_throttle_after(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        if self.metadata.throttling_after_auth is None:
            return
        for throttle in self.metadata.throttling_after_auth:
            assert isinstance(throttle, SyncThrottle)  # noqa: S101
            throttle(self, controller, self._sync_lock)

    # Async checks:

    async def _run_async_checks(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        # First round of throttling:
        await self._run_async_throttle_before(controller)
        # Negotiate response:
        self.response_negotiator(controller.request)
        # Auth:
        await self._run_async_auth(controller)
        # Second round of throttling:
        await self._run_async_throttle_after(controller)

    async def _run_async_throttle_before(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        if self.metadata.throttling_before_auth is None:
            return
        for throttle in self.metadata.throttling_before_auth:
            assert isinstance(throttle, AsyncThrottle)  # noqa: S101
            # We have to check them in sync one by one :(
            await throttle(self, controller, self._async_lock)  # noqa: WPS476

    async def _run_async_auth(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        if self.metadata.auth is None:
            return
        for auth in self.metadata.auth:
            assert isinstance(auth, AsyncAuth)  # noqa: S101
            authed_by = await auth(self, controller)  # noqa: WPS476
            if authed_by is not None:
                controller.request.__dmr_auth__ = authed_by  # type: ignore[attr-defined]
                return
        raise NotAuthenticatedError

    async def _run_async_throttle_after(
        self,
        controller: 'Controller[BaseSerializer]',
    ) -> None:
        if self.metadata.throttling_after_auth is None:
            return
        for throttle in self.metadata.throttling_after_auth:
            assert isinstance(throttle, AsyncThrottle)  # noqa: S101
            # We have to check them in sync one by one :(
            await throttle(self, controller, self._async_lock)  # noqa: WPS476

    # Utils:

    def _make_http_response(
        self,
        controller: 'Controller[BaseSerializer]',
        raw_data: Any | HttpResponse,
    ) -> HttpResponseBase:
        """
        Returns the actual ``HttpResponse`` object after optional validation.

        If it is already the :class:`django.http.HttpResponse` object,
        just validates it before returning.
        """
        try:
            return self._validate_response(controller, raw_data)
        except (  # noqa: WPS239
            ResponseSchemaError,
            ValidationError,
            DataRenderingError,
            InternalServerError,
        ) as exc:
            # We can't call `self.handle_error` or `self.handle_async_error`
            # in exception handlers here,
            # because it is too late. Since `ResponseSchemaError`
            # happened most likely because the return
            # schema validation was not successful.
            return controller.to_error(
                controller.format_error(exc),
                status_code=exc.status_code,
            )

    def _validate_response(
        self,
        controller: 'Controller[BaseSerializer]',
        response_data: Any | HttpResponseBase,
    ) -> HttpResponseBase:
        if isinstance(response_data, HttpResponseBase):
            return self.response_validator.validate_response(
                self,
                controller,
                response_data,
            )

        validated = self.response_validator.validate_modification(
            self,
            controller,
            response_data,
        )
        return self._build_new_response(controller, validated)

    def _build_new_response(
        self,
        controller: 'Controller[BaseSerializer]',
        validated: 'ValidatedModification',
    ) -> HttpResponseBase:
        return controller.to_response(
            validated.raw_data,
            status_code=validated.status_code,
            headers=validated.headers,
            cookies=validated.cookies,
            renderer=validated.renderer,
        )

    def _global_error_handler(
        self,
        controller: 'Controller[BaseSerializer]',
        exc: Exception,
    ) -> HttpResponse:
        """
        Import the global error handling and call it.

        If not class level error handling has happened.
        """
        return resolve_setting(  # type: ignore[no-any-return]
            Settings.global_error_handler,
            import_string=True,
        )(self, controller, exc)
