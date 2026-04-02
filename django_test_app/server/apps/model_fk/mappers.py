from typing import final

import attrs
from django.db.models import QuerySet

from server.apps.model_fk.models import Role, Tag, User
from server.apps.model_fk.serializers import RoleSchema, TagSchema, UserSchema


@final
@attrs.define(frozen=True)
class TagMap:
    def single(self, tag: Tag) -> TagSchema:
        return TagSchema(name=tag.name)

    def multiple(self, tags: QuerySet[Tag]) -> list[TagSchema]:
        return [self.single(tag) for tag in tags]


@final
@attrs.define(frozen=True)
class RoleMap:
    def single(self, role: Role) -> RoleSchema:
        return RoleSchema(name=role.name)


@final
@attrs.define(frozen=True)
class UserMap:
    _role: RoleMap
    _tag: TagMap

    def single(self, user: User) -> UserSchema:
        return UserSchema(
            id=user.pk,
            email=user.email,
            created_at=user.created_at,
            role=self._role.single(user.role),
            tags=self._tag.multiple(user.tags.all()),
        )

    def multiple(self, users: QuerySet[User]) -> list[UserSchema]:
        # TODO: don't forget about pagination!
        return [self.single(user) for user in users]
