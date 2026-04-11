import abc
from itertools import chain
from typing import TYPE_CHECKING

from typing_extensions import override

from dmr.headers import HeaderSpec

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
    from dmr.serializer import BaseSerializer
    from dmr.throttling.base import (
        _BaseThrottle,  # pyright: ignore[reportPrivateUsage]
    )


class BaseResponseHeadersProvider:
    @abc.abstractmethod
    def provide_headers_specs(self) -> dict[str, HeaderSpec]: ...

    @abc.abstractmethod
    def response_headers(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: '_BaseThrottle',
        remaining: int,
        reset: int,
    ) -> dict[str, str]: ...


class RateLimitIETFDraft(BaseResponseHeadersProvider):
    @override
    def provide_headers_specs(self) -> dict[str, HeaderSpec]:
        return {
            'RateLimit-Policy': HeaderSpec(
                description=(
                    'Description of all rate limiting policies '
                    'for this endpoint'
                ),
            ),
            'RateLimit': HeaderSpec(description='Current rate limiting state'),
        }

    @override
    def response_headers(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: '_BaseThrottle',
        remaining: int,
        reset: int,
    ) -> dict[str, str]:
        # Example headers:
        # `RateLimit-Policy: 30;w=60;name="ip", 100;w=3600;name="user"`
        # `RateLimit: "problemPolicy";r=0;t=10`

        return {
            'RateLimit-Policy': ', '.join(
                (
                    f'{throttle.max_requests};'
                    f'w={throttle.duration_in_seconds};'
                    f'name="{throttle.cache_key.name}"'
                )
                # However, it can't be `None`, since we are here:
                for throttle in (
                    chain(
                        endpoint.metadata.throttling_before_auth or (),
                        endpoint.metadata.throttling_after_auth or (),
                    )
                )
            ),
            'RateLimit': (
                f'"{throttle.cache_key.name}";r={remaining};t={reset}'
            ),
        }


class RetryAfter(BaseResponseHeadersProvider):
    @override
    def provide_headers_specs(self) -> dict[str, HeaderSpec]:
        return {
            'Retry-After': HeaderSpec(
                description=(
                    'Indicates how long the user agent should wait '
                    'before making a follow-up request'
                ),
            ),
        }

    @override
    def response_headers(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: '_BaseThrottle',
        remaining: int,
        reset: int,
    ) -> dict[str, str]:
        return {'Retry-After': str(reset)}


class XRateLimit(BaseResponseHeadersProvider):
    @override
    def provide_headers_specs(self) -> dict[str, HeaderSpec]:
        return {
            'X-RateLimit-Limit': HeaderSpec(
                description=(
                    'The maximum number of requests permitted '
                    'in the current time window'
                ),
            ),
            'X-RateLimit-Remaining': HeaderSpec(
                description=(
                    'The number of requests remaining '
                    'in the current time window'
                ),
            ),
            'X-RateLimit-Reset': HeaderSpec(
                description=(
                    'The number of seconds until the current '
                    'rate limit window resets'
                ),
            ),
        }

    @override
    def response_headers(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: '_BaseThrottle',
        remaining: int,
        reset: int,
    ) -> dict[str, str]:
        return {
            'X-RateLimit-Limit': str(throttle.max_requests),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset),
        }
