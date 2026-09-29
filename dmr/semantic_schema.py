import dataclasses
from abc import abstractmethod
from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING

from typing_extensions import override

from dmr.exceptions import EndpointMetadataError, ResponseSchemaError
from dmr.internal.types import StrOrPromise
from dmr.metadata import EndpointMetadata, ResponseSpec, ResponseSpecProvider

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.openapi.objects import (
        Reference,
        SecurityRequirement,
        SecurityScheme,
    )
    from dmr.serializer import BaseSerializer


class SecurityProvider:
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


class SecurityRequirementMerger:
    """
    Interface for things that can merge security requirements.

    What can do that?

    - :attr:`~dmr.openapi.generators.SecuritySchemeGenerator.security_merger`
      merges user provided ``security`` requirements
      with the ones generated from ``auth``
    - Semantic schema providers merge their own requirements
      with the ones generated from ``auth``,
      like :class:`~dmr.security.csrf.CSRFSemanticSchemaProvider` does

    .. versionadded:: 0.16.0
    """

    __slots__ = ()

    @abstractmethod
    def merge_security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        own_requirements: list['SecurityRequirement'],
        auth_requirements: list['SecurityRequirement'],
    ) -> list['SecurityRequirement']:
        """
        Merge own security requirements into the auth requirements.

        This can implement both ``OR`` and ``AND`` logic
        depending on the security logic:
        several alternative requirements mean ``OR``,
        several schemes in a single requirement mean ``AND``.

        Args:
            metadata: Metadata of the endpoint that is being generated.
            controller_cls: Controller class of this endpoint.
            own_requirements: Requirements of the thing that merges,
                for example, user provided ``security``.
            auth_requirements: Requirements generated from ``auth``,
                already processed by semantic schema providers.

        Returns:
            The final list of security requirements for the operation.

        """
        raise NotImplementedError


class OrSecurityRequirementMerger(SecurityRequirementMerger):
    """
    Merge security requirements as alternatives.

    All requirements are used as-is, own requirements are added
    after the auth ones. A client can satisfy any of them,
    this is what ``OR`` means in OpenAPI.

    This is the default value of
    :attr:`~dmr.openapi.generators.SecuritySchemeGenerator.security_merger`.

    Raises:
        EndpointMetadataError: When the same requirement is present
            more than once in the result. It usually means that
            ``security`` repeats what ``auth`` already documents.

    .. versionadded:: 0.16.0
    """

    __slots__ = ()

    @override
    def merge_security_requirements(
        self,
        metadata: EndpointMetadata,
        controller_cls: type['Controller[BaseSerializer]'],
        own_requirements: list['SecurityRequirement'],
        auth_requirements: list['SecurityRequirement'],
    ) -> list['SecurityRequirement']:
        """Add own requirements as alternatives to the auth ones."""
        merged = [*auth_requirements, *own_requirements]
        self._validate_no_duplicates(metadata, merged)
        return merged

    def _validate_no_duplicates(
        self,
        metadata: EndpointMetadata,
        requirements: list['SecurityRequirement'],
    ) -> None:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for requirement in requirements:
            for req in requirement:
                if req in seen:
                    duplicates.add(req)
                seen.add(req)
        if duplicates:
            raise EndpointMetadataError(
                f'Security requirements {duplicates!r} are duplicated '
                f'for {metadata.endpoint_name=}',
            )


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
    description: StrOrPromise | None = (
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
