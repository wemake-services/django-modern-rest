import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.metadata import EndpointMetadata
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.objects import SecurityRequirement
    from dmr.semantic_schema import AuthProvider
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True)
class SecuritySchemeGenerator:
    """
    Generator for OpenAPI Security Schemes.

    Responsible for processing authentication providers, extracting their
    security schemes, registering them in the context, and returning
    the corresponding security requirements for the operation.
    """

    _context: 'OpenAPIContext'

    def __call__(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list['SecurityRequirement'] | None:
        """
        Process auth providers and generate security requirements.

        Iterates over the provided authentication providers, registers their
        security schemes in the global registry, and collects their security
        usage requirements.

        When there are no auth providers but the document defines global
        ``security``, returns an explicit ``[]`` so the operation opts out
        of the global requirements instead of inheriting them.

        .. versionchanged:: 0.16.0
            Now accepts *metadata* and *controller_cls* parameters.

        """
        auth_providers = metadata.auth
        if not auth_providers:
            return [] if self._context.config.security else None

        requirements: list[SecurityRequirement] = []

        for auth in auth_providers:
            self._register_security_schemes(auth, metadata, controller_cls)

            requirements.extend(
                auth.security_requirements(metadata, controller_cls),
            )
        return requirements

    def _register_security_schemes(
        self,
        auth: 'AuthProvider',
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        for scheme_name, scheme in auth.security_schemes(
            metadata,
            controller_cls,
        ).items():
            self._context.registries.security_scheme.register(
                scheme_name,
                scheme,
            )
