from django.db import IntegrityError, transaction

from server.apps.models_example import serializers
from server.apps.models_example.models import Role, Tag, User


class UniqueEmailError(Exception):
    """Email must be unique."""


def user_create_service(user_schema: serializers.UserCreateSchema) -> User:
    """This is a function just for the demo purpose, it is usually a class."""
    with transaction.atomic():
        role = Role.objects.create(name=user_schema.role.name)

        try:
            user = User.objects.create(
                email=user_schema.email,
                role_id=role.pk,
            )
        except IntegrityError:
            raise UniqueEmailError from None

        # Handle m2m:
        tags = Tag.objects.bulk_create([
            Tag(name=tag.name) for tag in user_schema.tags
        ])
        user.tags.set(tags)
    return user
