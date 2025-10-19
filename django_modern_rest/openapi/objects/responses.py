from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from django_modern_rest.openapi.objects.reference import Reference
    from django_modern_rest.openapi.objects.response import Response

Responses = dict[str, Union['Response', 'Reference']]
"""
A container for the expected responses of an operation.

The container maps a HTTP response code to the expected response.
The documentation is not necessarily expected to cover all possible HTTP
response codes because they may not be known in advance.
However, documentation is expected to cover a successful operation
response and any known errors. The default MAY be used as a default response
object for all HTTP codes that are not covered individually by the Responses
Object. The Responses Object MUST contain at least one response code,
and if only one response code is provided it SHOULD be the response for a
successful operation call.
"""
