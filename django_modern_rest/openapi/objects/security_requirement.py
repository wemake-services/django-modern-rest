from typing import TypeAlias

SecurityRequirement: TypeAlias = dict[str, list[str]]
"""
Lists the required security schemes to execute this operation.

The name used for each property MUST correspond to a security scheme
declared in the Security Schemes under the Components Object.
Security Requirement Objects that contain multiple schemes require that all
schemes MUST be satisfied for a request to be authorized. This enables support
for scenarios where multiple query parameters or HTTP headers are required
to convey security information. When a list of Security Requirement Objects
is defined on the OpenAPI Object or Operation Object, only one of the
Security Requirement Objects in the list needs to be
satisfied to authorize the request.
"""
