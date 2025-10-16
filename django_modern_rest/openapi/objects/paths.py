from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects import PathItem

Paths = dict[str, 'PathItem']
