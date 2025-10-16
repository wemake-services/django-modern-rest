from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.response import OpenAPIResponse

Responses = dict[str, Union['OpenAPIResponse', 'Reference']]
