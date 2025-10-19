from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.path_item import PathItem
    from django_modern_rest.openapi.objects.reference import Reference

Callback = dict[str, Union['PathItem', 'Reference']]
"""
A map of possible out-of band callbacks related to the parent operation.

Each value in the map is a Path Item Object that describes a set of requests
that may be initiated by the API provider and the expected responses.
The key value used to identify the path item object is an expression,
evaluated at runtime, that identifies a URL to use for the callback operation.
"""
