import dataclasses
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.objects import SecurityRequirement
    from dmr.security import AsyncAuth, SyncAuth
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
        auth_providers: Sequence['SyncAuth | AsyncAuth'] | None,
        serializer: type['BaseSerializer'],
        security: Sequence['SecurityRequirement'] | None = None,
    ) -> list['SecurityRequirement'] | None:
        """
        Process auth providers and generate security requirements.

        Iterates over the provided authentication providers, registers their
        security schemes in the global registry, and collects their security
        usage requirements.

        Explicitly declared ``security`` requirements are preserved as well:
        they are merged with the ones derived from ``auth_providers``, so
        endpoints can document external security mechanisms (for example, one
        enforced by a proxy or another service) next to the internal ones.
        """
        requirements: list[SecurityRequirement] = list(security or [])

        for auth in auth_providers or ():
            schemes = auth.security_schemes
            if schemes:
                for scheme_name, scheme in schemes.items():
                    self._context.registries.security_scheme.register(
                        scheme_name,
                        scheme,
                    )

            requirements.append(auth.security_requirement)
        return requirements or None
