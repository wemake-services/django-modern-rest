import dataclasses
from abc import abstractmethod
from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING

from typing_extensions import override

from dmr.exceptions import ResponseSchemaError
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider

if TYPE_CHECKING:
    from django.utils.functional import (
        _StrOrPromise,  # pyright: ignore[reportPrivateUsage]
    )

    from dmr.controller import Controller
    from dmr.openapi.objects import (
        Reference,
        SecurityRequirement,
        SecurityScheme,
    )
    from dmr.serializer import BaseSerializer


class AuthProvider:
    """
    Provides security schemes and security requirements.

    .. versionadded:: 0.16.0
    """

    __slots__ = ()

    @abstractmethod
    def security_schemes(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> dict[str, 'SecurityScheme | Reference']:
        """Provides a security schema definition."""
        raise NotImplementedError

    @abstractmethod
    def security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list['SecurityRequirement']:
        """Provides a security schema usage requirement."""
        raise NotImplementedError

    def inject_requirements(
        self,
        own_requirements: list['SecurityRequirement'],
        auth_requirements: list['SecurityRequirement'],
    ) -> list['SecurityRequirement']:
        """
        Inject semantic scheme requirements into regular auth requirements.

        This can implement both `OR` and `AND` logic
        dependending on the auth logic.

        This method is only called by semantic schema providers
        when generating auth requirements.
        By default just returns the original auth requirements.
        """
        return auth_requirements


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class ResponseValidationSpecProvider(ResponseSpecProvider):
    """
    Provide response specs for response schema validation.

    Does not add itself for endpoints
    that have ``validate_responses`` turned off.

    Should be added to :data:`dmr.settings.Settings.semantic_schema_providers`
    setting.

    Attributes:
        status_code: Status code to be returned when validation error happens.
        description: Response spec description for humans.

    .. versionadded:: 0.16.0
    """

    status_code: HTTPStatus = ResponseSchemaError.status_code
    description: '_StrOrPromise | None' = (
        'Raised when returned response does not match the response schema'
    )

    @override
    def provide_response_specs(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        existing_responses: Mapping[HTTPStatus, ResponseSpec],
    ) -> list[ResponseSpec]:
        """Provides responses that can happen when returning invalid data."""
        return (
            self._add_new_response(
                ResponseSpec(
                    return_type=controller_cls.error_model,
                    status_code=self.status_code,
                    description=self.description,
                ),
                existing_responses,
            )
            # When validation is disabled, `ResponseSchemaError` can't happen.
            if metadata.validate_responses
            else []
        )
