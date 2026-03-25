import dataclasses
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dmr.metadata import EndpointMetadata
    from dmr.openapi.core.context import OpenAPIContext
    from dmr.serializer import BaseSerializer


@dataclasses.dataclass(frozen=True, slots=True)
class OperationIdGenerator:
    """
    Generator for unique OpenAPI operation IDs.

    The Operation ID builder is responsible for creating unique
    operation IDs for OpenAPI operations.
    It uses the explicit ``operation_id`` from endpoint metadata if available,
    otherwise generates one from the HTTP method and path following
    ``RFC 3986`` specifications.
    All generated operation IDs are registered in the registry to ensure
    uniqueness across the OpenAPI specification.
    """

    _context: 'OpenAPIContext'

    def __call__(
        self,
        path: str,
        suffix: str,
        metadata: 'EndpointMetadata',
        serializer: type['BaseSerializer'],
    ) -> str:
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
        operation_id = metadata.method.lower() + ''.join(
            self._tokenize_path(suffix + path),
        )

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
        # Remove `{}` from path variables (e.g., {id}, {user_id})
        path = path.replace('{', '').replace('}', '')
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
