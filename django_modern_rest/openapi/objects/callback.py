from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.path_item import PathItem
    from django_modern_rest.openapi.objects.reference import Reference

Callback = dict[str, Union['PathItem', 'Reference']]
