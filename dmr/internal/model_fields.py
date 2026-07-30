import datetime as dt
from typing import TypeAlias

from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.db.models.expressions import Combinable

_BaseFkData: TypeAlias = int | str | Combinable
_BaseDtData: TypeAlias = str | dt.datetime | Combinable

UserForeignKey: TypeAlias = (
    'models.ForeignKey[_BaseFkData | AbstractBaseUser, AbstractBaseUser]'
)
CharField: TypeAlias = 'models.CharField[_BaseFkData, str]'
DateTimeField: TypeAlias = 'models.DateTimeField[_BaseDtData, dt.datetime]'
DateTimeFieldNullable: TypeAlias = (
    'models.DateTimeField[_BaseDtData | None, dt.datetime | None]'
)
