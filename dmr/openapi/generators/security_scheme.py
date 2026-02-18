import dataclasses
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.objects import SecurityRequirement
    from dmr.security import AsyncAuth, SyncAuth


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
        auth_providers: Sequence['SyncAuth | AsyncAuth'] | None,
    ) -> list['SecurityRequirement'] | None:
        """
        Process auth providers and generate security requirements.

        Iterates over the provided authentication providers, registers their
        security schemes in the global registry, and collects their security
        usage requirements.
        """
        if not auth_providers:
            return None

        requirements: list[SecurityRequirement] = []

        for auth in auth_providers:
            schemes = auth.security_scheme.security_schemes
            if schemes:
                for name, scheme in schemes.items():
                    self._context.registries.security_scheme.register(
                        name,
                        scheme,
                    )

            requirements.append(auth.security_requirement)
        return requirements
