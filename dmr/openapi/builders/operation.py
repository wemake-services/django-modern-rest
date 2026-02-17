import dataclasses
import re
from typing import TYPE_CHECKING

from django_modern_rest.openapi.objects import Operation

if TYPE_CHECKING:
    from django_modern_rest.metadata import EndpointMetadata
    from django_modern_rest.openapi.core.context import OpenAPIContext


@dataclasses.dataclass(frozen=True, slots=True)
class OperationBuilder:
    """
    Build for OpenAPI Operation objects.

    The ``Operation`` builder is responsible for creating OpenAPI
    objects that describe individual API operations (HTTP methods like GET,
    POST, etc.) for a specific endpoint. It extracts metadata from the
    endpoint and generates a complete Operation specification.
    """

    metadata: 'EndpointMetadata'

    # NOTE: We are currently maintaining `context` for backward compatibility.
    # In future, we must encapsulate it.
    def __call__(self, context: 'OpenAPIContext', path: str) -> Operation:
        """Builde an OpenAPI Operation from an endpoint."""
        operation_id = context.generators.operation_id(self.metadata, path)
        request_body = context.generators.request_body(self.metadata)
        responses = context.generators.response(self.metadata)
        params_list = context.generators.parameter(self.metadata)
        security = context.generators.security_scheme(self.metadata.auth)

        return Operation(
            tags=self.metadata.tags,
            summary=self.metadata.summary,
            description=self.metadata.description,
            deprecated=self.metadata.deprecated,
            security=security,
            external_docs=self.metadata.external_docs,
            servers=self.metadata.servers,
            callbacks=self.metadata.callbacks,
            operation_id=operation_id,
            request_body=request_body,
            responses=responses,
            parameters=params_list,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class OperationIDBuilder:
    """
    Builder for unique OpenAPI operation IDs.

    The Operation ID builder is responsible for creating unique
    operation IDs for OpenAPI operations.
    It uses the explicit ``operation_id`` from endpoint metadata if available,
    otherwise generates one from the HTTP method and path following
    ``RFC 3986`` specifications.
    All generated operation IDs are registered in the registry to ensure
    uniqueness across the OpenAPI specification.
    """

    _context: 'OpenAPIContext'

    def __call__(self, metadata: 'EndpointMetadata', path: str) -> str:
        """
        Generate a unique operation ID for an OpenAPI operation.

        Uses the explicit ``operation_id`` from endpoint metadata if available,
        otherwise generates one from the HTTP method and path. The operation ID
        is registered in the registry to ensure uniqueness.
        """
        operation_id = metadata.operation_id

        if operation_id is not None:
            self._context.registries.operation_id.register(operation_id)
            return operation_id

        # Generate operation_id from path and method
        tokens = self._tokenize_path(path)
        method = metadata.method.lower()
        operation_id = self._build_operation_id(method, tokens)

        self._context.registries.operation_id.register(operation_id)
        return operation_id

    def _tokenize_path(self, path: str) -> list[str]:  # noqa: WPS210
        """
        Tokenize path into meaningful parts for operation ID generation.

        According to RFC 3986:
        - Removes path variables (e.g., {id}, {user_id})
        - Splits by '/' (gen-delim, path segment separator)
        - Normalizes unreserved characters: '-', '_', '.', '~' are treated
            as word separators for camelCase conversion
        - Removes reserved characters that shouldn't appear in operation IDs
        """
        # Remove path variables (e.g., {id}, {user_id})
        path = re.sub(pattern=r'\{[\w\-]+\}', repl='', string=path)
        tokenized_path = path.strip('/').split('/')

        normalized_tokens: list[str] = []
        for token in tokenized_path:
            if not token:
                continue

            # Remove reserved characters (gen-delims and sub-delims)
            # Keep only unreserved: ALPHA, DIGIT, '-', '.', '_', '~'
            # (RFC 3986, section 2.3)
            cleaned_token = re.sub(pattern=r'[^\w\-._~]', repl='', string=token)

            if not cleaned_token:
                continue

            # Split to preserve word boundaries
            parts = re.split(r'[-_.~]+', cleaned_token)
            normalized_parts = [part.capitalize() for part in parts if part]

            if normalized_parts:
                normalized_tokens.append(''.join(normalized_parts))

        return normalized_tokens

    def _build_operation_id(self, method: str, tokens: list[str]) -> str:
        """Build operation ID from HTTP method and path tokens."""
        return method + ''.join(tokens) if tokens else method
