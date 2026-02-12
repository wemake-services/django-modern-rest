from django.db import transaction

from server.apps.models_example import serializers
from server.apps.models_example.models import Role, Tag, User


class UniqueEmailError(Exception):
    """Email must be unique."""


def user_create_service(user_schema: serializers.UserCreateSchema) -> User:
    """This is a function just for the demo purpose, it is usually a class."""
    if User.objects.filter(email=user_schema.email).exists():
        raise UniqueEmailError

    with transaction.atomic():
        role = Role.objects.create(name=user_schema.role.name)
        user = User.objects.create(
            email=user_schema.email,
            role_id=role.pk,
        )

        # Handle m2m:
        tags = Tag.objects.bulk_create([
            Tag(name=tag.name) for tag in user_schema.tag_list
        ])
        user.tags.set(tags)
    return user
