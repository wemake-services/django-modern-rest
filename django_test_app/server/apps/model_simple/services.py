from django.db import IntegrityError
from django.db.models import QuerySet

from server.apps.model_simple.models import User
from server.apps.model_simple.serializers import SimpleUserCreateSchema


class UniqueConstraintError(Exception):
    """Fields ``email`` and ``customer_service_uid`` must be unique."""


def user_create_service(user_schema: SimpleUserCreateSchema) -> User:
    """This is a function just for the demo purpose, it is usually a class."""
    try:
        return User.objects.create(
            email=user_schema.email,
            customer_service_uid=user_schema.customer_service_uid,
        )
    except IntegrityError:
        # We don't raise `IntegrityError` here, because we prefer domain
        # exceptions over Django ones. It is much easier to manage.
        raise UniqueConstraintError from None


def user_list_service() -> QuerySet[User]:
    """Return all users."""
    # Only can exclude fields that we won't use by passing as a param
    # `UserSchema.__struct_fields__` tuple and calling `.only(*fields)` here:
    return User.objects.all()
