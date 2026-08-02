from typing import Final, final

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

_USERNAME_SIZE: Final = 150


@final
class ApiUser(AbstractBaseUser):
    """Custom user model, it is not ``settings.AUTH_USER_MODEL``."""

    username = models.CharField(max_length=_USERNAME_SIZE, unique=True)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = 'username'  # noqa: WPS115
