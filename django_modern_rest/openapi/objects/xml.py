from dataclasses import dataclass
from typing import final

from django_modern_rest.openapi.objects.base import BaseObject


@final
@dataclass(frozen=True, kw_only=True, slots=True)
class XML(BaseObject):
    """
    A metadata object that allows for more fine-tuned XML model definitions.

    When using arrays, XML element names are not inferred
    (for singular/plural forms) and the name property `SHOULD` be used
    to add that information.
    """

    name: str | None = None
    namespace: str | None = None
    prefix: str | None = None
    attribute: bool = False
    wrapped: bool = False
