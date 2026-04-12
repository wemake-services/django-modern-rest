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
    """Base class for all header providers."""

    @abc.abstractmethod
    def provide_headers_specs(self) -> dict[str, HeaderSpec]:
        """Provide a spec for headers for the OpenAPI."""
        raise NotImplementedError

    @abc.abstractmethod
    def response_headers(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        throttle: '_BaseThrottle',
        remaining: int,
        reset: int,
    ) -> dict[str, str]:
        """Return a dict of rendered headers to be added to the response."""
        raise NotImplementedError


class RetryAfter(BaseResponseHeadersProvider):
    """
    Provides ``Retry-After`` header.

    It is based on the existing spec.

    .. seealso::

      `RFC-6585 <https://datatracker.ietf.org/doc/html/rfc6585#section-4>`_
      and
      `RFC-7231 <https://datatracker.ietf.org/doc/html/rfc7231#section-7.1.3>`_

    """

    @override
    def provide_headers_specs(self) -> dict[str, HeaderSpec]:
        """Provides headers specification."""
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
        """Returns the formatted response headers."""
        return {'Retry-After': str(reset)}


class XRateLimit(BaseResponseHeadersProvider):
    """
    Provides ``X-RateLimit`` headers.

    There headers inside:

    - ``X-RateLimit-Limit``
    - ``X-RateLimit-Remaining``
    - ``X-RateLimit-Reset``

    It is based on popular convention and does not have a formal spec.

    .. seealso::

        https://http.dev/x-ratelimit-limit

    """

    @override
    def provide_headers_specs(self) -> dict[str, HeaderSpec]:
        """Provides headers specification."""
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
        """Returns the formatted response headers."""
        return {
            'X-RateLimit-Limit': str(throttle.max_requests),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset),
        }


class RateLimitIETFDraft(BaseResponseHeadersProvider):
    """
    Provides ``RateLimit`` and ``RateLimit-Policy`` headers.

    It is based on the latest draft of the ratelmiting headers spec.

    .. seealso::

        https://www.ietf.org/archive/id/draft-ietf-httpapi-ratelimit-headers-10.html

    """

    @override
    def provide_headers_specs(self) -> dict[str, HeaderSpec]:
        """Provides headers specification."""
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
        """Returns the formatted response headers."""
        # Example headers:
        # `RateLimit-Policy: 30;w=60;name="ip", 100;w=3600;name="user"`
        # `RateLimit: "problemPolicy";r=0;t=10`

        return {
            'RateLimit-Policy': ', '.join(
                (
                    f'{throttle.max_requests};'  # noqa: WPS237
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
                f'"{throttle.cache_key.name}";r={remaining};t={reset}'  # noqa: WPS237
            ),
        }
