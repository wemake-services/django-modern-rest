from typing import Any, TypeVar

# TODO(sobolevn): release new `punq` version:
import punq  # type: ignore[import-untyped]

from server.apps.model_fk.mappers import RoleMap, TagMap, UserMap
from server.apps.model_fk.services import (
    RoleCreate,
    TagsCreate,
    UserCreate,
    UserList,
)

_ItemT = TypeVar('_ItemT')


class HasContainer:
    __slots__ = ('_container',)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Will be created in import-time:
        self._container = self._create_container()

    def resolve(self, thing: type[_ItemT]) -> _ItemT:
        return self._container.resolve(thing)  # type: ignore[no-any-return]

    def _create_container(self) -> punq.Container:
        container = punq.Container()
        container.register(TagMap)
        container.register(RoleMap)
        container.register(UserMap)

        container.register(TagsCreate)
        container.register(RoleCreate)
        container.register(UserCreate)
        container.register(UserList)

        return container
