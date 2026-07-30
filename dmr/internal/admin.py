from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from django.contrib import admin
from django.db.models import Model

_ModelT = TypeVar('_ModelT', bound=Model)

if TYPE_CHECKING:
    ModelAdmin = admin.ModelAdmin
else:

    class ModelAdmin(admin.ModelAdmin, Generic[_ModelT]): ...  # noqa: D101, WPS604
