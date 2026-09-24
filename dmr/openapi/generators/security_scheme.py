import dataclasses
import itertools
from typing import TYPE_CHECKING, TypeAlias

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


_SecuritySchemes: TypeAlias = dict[str, 'SecurityScheme | Reference']


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
        # Can be provided via: `metadata.auth`, `OpenAPIConfig.security`,
        # semantic schema providers.
        # We always use  `metadata.auth` as-is.
        # `OpenAPIConfig.security` is applied in config merger.
        # We process all existing `metadata.auth` security requirements
        # to possibly inject extra ones from semantic schemas.
        self._register_auth_security_schemes(metadata, controller_cls)
        requirements = self._prepare_requirements(metadata, controller_cls)
        requirements, semantic_schemes = self._inject_semantic_schema(
            metadata,
            controller_cls,
            requirements,
        )
        self._register_security_schemes(
            metadata,
            controller_cls,
            semantic_schemes,
        )

        # Finally, return the result:
        if not requirements:
            # If global security is set,
            # but this endpoint does not have any auth,
            # it must return explicit `[]`, so it's auth would be re-written:
            return [] if self._context.config.security else None
        return requirements

    def _register_auth_security_schemes(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> None:
        for auth in metadata.auth or []:
            self._register_security_schemes(
                metadata,
                controller_cls,
                auth.security_schemes(
                    metadata,
                    controller_cls,
                ),
            )

    def _register_security_schemes(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
        security_schemes: _SecuritySchemes,
    ) -> None:
        for scheme_name, scheme in security_schemes.items():
            if (
                not metadata.semantic_auth
                or scheme_name in metadata.exclude_semantic_auth
            ):
                continue
            self._context.registries.security_scheme.register(
                scheme_name,
                scheme,
            )

    def _prepare_requirements(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
    ) -> list['SecurityRequirement']:
        requirements: list[SecurityRequirement] = []
        for auth in metadata.auth or []:
            requirements.extend(
                new_requirement
                for requirement in auth.security_requirements(
                    metadata,
                    controller_cls,
                )
                if (
                    new_requirement := _filter_requirement(
                        requirement,
                        metadata,
                    )
                )
                is not None
            )
        return requirements

    def _inject_semantic_schema(
        self,
        metadata: 'EndpointMetadata',
        controller_cls: type['Controller[BaseSerializer]'],
        requirements: list['SecurityRequirement'],
    ) -> tuple[
        list['SecurityRequirement'],
        _SecuritySchemes,
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
        used_requirements = frozenset(
            itertools.chain.from_iterable(req.keys() for req in requirements),
        )
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


def _filter_requirement(
    requirement: 'SecurityRequirement',
    metadata: 'EndpointMetadata',
) -> 'SecurityRequirement | None':
    return {
        req_name: req_value
        for req_name, req_value in requirement.items()
        if (
            metadata.semantic_auth
            and req_name not in metadata.exclude_semantic_auth
        )
    } or None
