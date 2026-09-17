import dataclasses
import itertools
from collections.abc import Sequence
from typing import TYPE_CHECKING

from dmr.exceptions import EndpointMetadataError

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.metadata import EndpointMetadata
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.openapi.objects import (
        Reference,
        SecurityRequirement,
        SecurityScheme,
    )
    from dmr.semantic_schema import AuthProvider
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True)
class SecuritySchemeGenerator:
    """
    Generator for OpenAPI Security Schemes.

    Responsible for processing authentication providers, extracting their
    security schemes, registering them in the context, and returning
    the corresponding security requirements for the operation.

    User provided requirements from ``metadata.security`` are passed
    through as-is, their schemes are never registered. We only validate
    that they do not reuse the scheme names that ``auth`` generates.
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

        User provided ``security`` requirements are added after the auth ones.
        Their security schemes are not registered,
        users must declare them in the OpenAPI config.
        They also must not reuse the scheme names that ``auth`` generates,
        :class:`~dmr.exceptions.EndpointMetadataError` is raised when they do.

        When there are no requirements but the document defines global
        ``security``, returns an explicit ``[]`` so the operation opts out
        of the global requirements instead of inheriting them.

        .. versionchanged:: 0.16.0
            Now accepts *metadata* and *controller_cls* parameters.
            User provided ``security`` requirements are added as well.

        """
        # How it works?
        #
        # First, of all: we have security specs and security requirements.
        # Secondly: we have several different ways of how they can be provided.
        #
        # Security schemes
        # ----------------
        # Can be provided via: `metadata.auth` classes,
        # `OpenAPIConfig.components.security_schemes` field,
        # semantic schema providers.
        # We always use `metadata.auth` as-is.
        # `security_schemes` is applied in config merger.
        # We only register security schemes from semantic schema providers,
        # that are actually used.
        #
        # Security requirements
        # ---------------------
        # Can be provided via: `metadata.auth`, `metadata.security`,
        # `OpenAPIConfig.security`, semantic schema providers.
        # We always use  `metadata.auth` as-is.
        # `OpenAPIConfig.security` is applied in config merger.
        # We process all existing `metadata.auth` security requirements
        # to possibly inject extra ones from semantic schemas.
        # User provided `metadata.security` is added last.
        auth_schemes = self._register_security_schemes(
            metadata,
            controller_cls,
        )
        requirements = self._prepare_requirements(metadata, controller_cls)
        requirements, semantic_schemes = self._inject_semantic_schema(
            metadata,
            controller_cls,
            requirements,
        )
        for scheme_name, scheme in semantic_schemes.items():
            self._context.registries.security_scheme.register(
                scheme_name,
                scheme,
            )

        self._validate_no_auth_scheme_overlap(
            metadata,
            auth_schemes
            | semantic_schemes.keys()
            | _scheme_names(
                requirements,
            ),
        )
        requirements.extend(metadata.security or ())

        # Finally, return the result:
        if not requirements:
            # If global security is set,
            # but this endpoint does not have any auth,
            # it must return explicit `[]`, so it's auth would be re-written:
            return [] if self._context.config.security else None
        return requirements

    def _register_security_schemes(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> set[str]:
        registered: set[str] = set()
        for auth in metadata.auth or []:
            for scheme_name, scheme in auth.security_schemes(
                metadata,
                controller_cls,
            ).items():
                self._context.registries.security_scheme.register(
                    scheme_name,
                    scheme,
                )
                registered.add(scheme_name)
        return registered

    def _validate_no_auth_scheme_overlap(
        self,
        metadata: 'EndpointMetadata',
        auth_schemes: set[str],
    ) -> None:
        if not metadata.security:
            return

        intersection = sorted(
            _scheme_names(metadata.security) & auth_schemes,
        )
        if intersection:
            raise EndpointMetadataError(
                f'Security schemes {intersection} are already generated '
                f'by auth providers for {metadata.endpoint_name=}, '
                'check `security` in settings, on the controller, '
                'and on the endpoint',
            )

    def _prepare_requirements(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list['SecurityRequirement']:
        requirements: list[SecurityRequirement] = []
        for auth in metadata.auth or []:
            requirements.extend(
                auth.security_requirements(metadata, controller_cls),
            )
        return requirements

    def _inject_semantic_schema(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
        requirements: list['SecurityRequirement'],
    ) -> tuple[
        list['SecurityRequirement'],
        dict[str, 'SecurityScheme | Reference'],
    ]:
        semantic_providers = self._resolve_auth_semantic_providers(
            metadata,
            controller_cls,
        )

        new_requirements: list[SecurityRequirement] = []
        for provider in semantic_providers:
            semantic_requirements = provider.security_requirements(
                metadata,
                controller_cls,
            )
            new_requirements.extend(
                provider.inject_requirements(
                    semantic_requirements,
                    requirements,
                ),
            )

        return new_requirements, self._semantic_security_schemes(
            metadata,
            controller_cls,
            semantic_providers,
            new_requirements,
        )

    def _semantic_security_schemes(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
        semantic_providers: list['AuthProvider'],
        requirements: list['SecurityRequirement'],
    ) -> dict[str, 'SecurityScheme | Reference']:
        used_requirements = _scheme_names(requirements)
        schemes = [
            provider.security_schemes(metadata, controller_cls)
            for provider in semantic_providers
        ]
        used_schemes: dict[str, SecurityScheme | Reference] = {}
        for scheme in schemes:
            used_schemes.update({
                scheme_name: scheme[scheme_name]
                for scheme_name in scheme
                if scheme_name in used_requirements
            })
        return used_schemes

    def _resolve_auth_semantic_providers(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list['AuthProvider']:
        from dmr.semantic_schema import AuthProvider  # noqa: PLC0415
        from dmr.settings import Settings, resolve_setting  # noqa: PLC0415

        return [
            provider
            for provider in resolve_setting(Settings.semantic_schema_providers)
            if isinstance(provider, AuthProvider)
        ]


def _scheme_names(
    requirements: 'Sequence[SecurityRequirement]',
) -> frozenset[str]:
    return frozenset(
        itertools.chain.from_iterable(
            requirement.keys() for requirement in requirements
        ),
    )
