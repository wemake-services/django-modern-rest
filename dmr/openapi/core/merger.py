import dataclasses
from typing import TYPE_CHECKING, TypeVar

from dmr.openapi.objects import Components, Info, Paths
from dmr.openapi.openapi import OpenAPI

if TYPE_CHECKING:
    from dmr.openapi.core.context import OpenAPIContext


@dataclasses.dataclass(frozen=True, slots=True)
class ConfigMerger:
    """
    Merges OpenAPI configuration with generated paths and components.

    This class is responsible for combining the OpenAPI configuration
    from the context with the generated paths and components to create
    a complete OpenAPI specification object.
    """

    context: 'OpenAPIContext'

    def __call__(self, paths: Paths, components: Components) -> OpenAPI:
        """Merge paths and components with configuration."""
        config = self.context.config
        return OpenAPI(
            openapi=config.openapi_version,
            info=Info(
                title=config.title,
                version=config.version,
                summary=config.summary,
                description=config.description,
                terms_of_service=config.terms_of_service,
                contact=config.contact,
                license=config.license,
            ),
            servers=config.servers,
            tags=config.tags,
            external_docs=config.external_docs,
            security=config.security,
            webhooks=config.webhooks,
            paths=paths,
            components=self._merge_components(config.components, components),
        )

    def _merge_components(
        self,
        existing: Components | list[Components] | None,
        to_merge: Components,
    ) -> Components:
        """Merge :class:`dmr.openapi.objects.Components` defs together."""
        if not existing:
            return to_merge
        if isinstance(existing, list):
            temporary: Components | None = None
            for subcomponents in existing:
                temporary = self._merge_components(temporary, subcomponents)
            # for mypy: it can't be nothing but `Components` now:
            assert isinstance(temporary, Components)  # noqa: S101
            existing = temporary

        return Components(
            schemas=_merge_unique(existing.schemas, to_merge.schemas),
            responses=_merge_unique(existing.responses, to_merge.responses),
            parameters=_merge_unique(existing.parameters, to_merge.parameters),
            examples=_merge_unique(existing.examples, to_merge.examples),
            request_bodies=_merge_unique(
                existing.request_bodies,
                to_merge.request_bodies,
            ),
            headers=_merge_unique(existing.headers, to_merge.headers),
            security_schemes=_merge_unique(
                existing.security_schemes,
                to_merge.security_schemes,
            ),
            links=_merge_unique(existing.links, to_merge.links),
            callbacks=_merge_unique(existing.callbacks, to_merge.callbacks),
            path_items=_merge_unique(existing.path_items, to_merge.path_items),
        )


_ThingT = TypeVar('_ThingT')


def _merge_unique(
    existing: dict[str, _ThingT] | None,
    to_merge: dict[str, _ThingT] | None,
) -> dict[str, _ThingT] | None:
    if existing is None:
        return to_merge or None
    if to_merge is None:
        return existing or None

    shared_keys = existing.keys() & to_merge.keys()
    if shared_keys:
        raise ValueError(
            f'Trying to merge components with shared keys: {shared_keys}',
        )
    return {**existing, **to_merge} or None
