from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.path_item import PathItem

Paths = dict[str, 'PathItem']
"""
Holds the relative paths to the individual endpoints and their operations.
The path is appended to the URL from the Server Object in order to construct
the full URL. The Paths MAY be empty, due to
Access Control List (ACL) constraints.
"""
