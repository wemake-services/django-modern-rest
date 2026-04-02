from collections.abc import Iterable
from typing import final

import attrs
from django.db import IntegrityError, transaction

from server.apps.model_fk.mappers import UserMap
from server.apps.model_fk.models import Role, Tag, User
from server.apps.model_fk.serializers import (
    RoleSchema,
    TagSchema,
    UserCreateSchema,
    UserSchema,
)


@final
class UniqueConstraintError(Exception):
    """Field ``email`` must be unique."""


@final
@attrs.define(frozen=True)
class TagsCreate:
    def __call__(self, tags: list[TagSchema]) -> Iterable[Tag]:
        """Service for creating new tags with unique names."""
        tags_names = {tag.name for tag in tags}
        # Create new tags and ignore existing ones in 1 query:
        Tag.objects.bulk_create(
            [Tag(name=tag) for tag in tags_names],
            ignore_conflicts=True,
        )
        # Since `bulk_create` does not return `ids`, we need to query them:
        return Tag.objects.in_bulk(
            tags_names,
            field_name='name',
        ).values()


@final
@attrs.define(frozen=True)
class RoleCreate:
    def __call__(self, role_schema: RoleSchema) -> Role:
        """Service for getting an existing role or creating a new one."""
        role, _ = Role.objects.get_or_create(name=role_schema.name)
        return role


@final
@attrs.define(frozen=True)
class UserCreate:
    _role_create: RoleCreate
    _tags_create: TagsCreate
    _mapper: UserMap

    def __call__(self, user_schema: UserCreateSchema) -> UserSchema:
        """Service to create new users."""
        return self._mapper.single(self._create_user(user_schema))

    def _create_user(self, user_schema: UserCreateSchema) -> User:
        with transaction.atomic():
            role = self._role_create(user_schema.role)

            try:
                user = User.objects.create(
                    email=user_schema.email,
                    role=role,
                )
            except IntegrityError:
                # We don't raise `IntegrityError` here, because we prefer domain
                # exceptions over Django ones. It is much easier to manage.
                raise UniqueConstraintError from None

            # Handle m2m:
            user.tags.set(self._tags_create(user_schema.tags))
        return user


@final
@attrs.define(frozen=True)
class UserList:
    _mapper: UserMap

    def __call__(self) -> list[UserSchema]:
        """Return all users."""
        return self._mapper.multiple(
            User.objects.select_related('role').prefetch_related('tags').all(),
        )
