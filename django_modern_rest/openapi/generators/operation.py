import re
from http import HTTPStatus
from types import MappingProxyType
from typing import TYPE_CHECKING, get_args

from django_modern_rest.metadata import ResponseSpec
from django_modern_rest.openapi.objects.media_type import MediaType
from django_modern_rest.openapi.objects.operation import Operation
from django_modern_rest.openapi.objects.parameter import Parameter
from django_modern_rest.openapi.objects.reference import Reference
from django_modern_rest.openapi.objects.request_body import RequestBody
from django_modern_rest.openapi.objects.response import Response
from django_modern_rest.openapi.objects.responses import Responses
from django_modern_rest.parsers import Parser

if TYPE_CHECKING:
    from django_modern_rest.endpoint import Endpoint
    from django_modern_rest.metadata import ComponentParserSpec
    from django_modern_rest.openapi.core.context import OpenAPIContext


_CONTEXT_TO_IN = MappingProxyType({
    'parsed_query': 'query',
    'parsed_path': 'path',
    'parsed_headers': 'header',
    'parsed_cookies': 'cookie',
})


class OperationGenerator:
    """
    Generator for OpenAPI Operation objects.

    The Operation Generator is responsible for creating OpenAPI Operation
    objects that describe individual API operations (HTTP methods like GET,
    POST, etc.) for a specific endpoint. It extracts metadata from the
    endpoint and generates a complete Operation specification.
    """

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Initialize the Operation Generator."""
        self.context = context

    def generate(self, endpoint: 'Endpoint', path: str) -> Operation:
        """Generate an OpenAPI Operation from an endpoint."""
        metadata = endpoint.metadata
        operation_id = self.context.operation_id_generator.generate(
            endpoint,
            path,
        )
        request_body = self._generate_request_body(
            metadata.component_parsers,
            metadata.parsers,
        )
        responses = self._generate_responses(
            metadata.responses,
            metadata.parsers,
        )
        params_list = self._generate_parameters(metadata.component_parsers)

        return Operation(
            tags=metadata.tags,
            summary=metadata.summary,
            description=metadata.description,
            deprecated=metadata.deprecated,
            security=(
                None
                if metadata.auth is None
                else [auth.security_requirement for auth in metadata.auth]
            ),
            external_docs=metadata.external_docs,
            servers=metadata.servers,
            callbacks=metadata.callbacks,
            operation_id=operation_id,
            request_body=request_body,
            responses=responses,
            parameters=params_list,
        )

    def _generate_parameters(
        self,
        parsers: 'list[ComponentParserSpec]',
    ) -> list[Parameter | Reference] | None:
        params_list: list[Parameter | Reference] = []

        for parser_cls, parser_args in parsers:
            param_in = _CONTEXT_TO_IN.get(parser_cls.context_name)

            if not param_in or not parser_args:
                continue

            params_list.extend(
                self.context.schema_generator.generate_parameters(
                    parser_args[0],
                    param_in,
                ),
            )

        return params_list or None

    def _generate_request_body(
        self,
        parsers: 'list[ComponentParserSpec]',
        request_parsers: 'dict[str, type[Parser]]',
    ) -> RequestBody | None:
        for parser, _ in parsers:
            # TODO: Do we need enum for context name?
            if parser.context_name != 'parsed_body':
                continue

            parser_type = get_args(parser)[0]
            reference = self.context.schema_generator.get_schema(parser_type)
            return RequestBody(
                content={
                    req_parser.content_type: MediaType(schema=reference)
                    for req_parser in request_parsers.values()
                },
                required=True,
            )
        return None

    def _generate_responses(
        self,
        responses: dict[HTTPStatus, ResponseSpec],
        request_parsers: 'dict[str, type[Parser]]',
    ) -> Responses:
        return {
            str(status_code.value): Response(
                description=status_code.phrase,
                content={
                    req_parser.content_type: MediaType(
                        schema=self.context.schema_generator.get_schema(
                            response_spec.return_type,
                        ),
                    )
                    for req_parser in request_parsers.values()
                },
            )
            for status_code, response_spec in responses.items()
        }


class OperationIDGenerator:
    """
    Generator for unique OpenAPI operation IDs.

    The Operation ID Generator is responsible for creating unique
    operation IDs for OpenAPI operations.
    It uses the explicit `operation_id` from endpoint metadata if available,
    otherwise generates one from the HTTP method and path following
    `RFC 3986` specifications.
    All generated operation IDs are registered in the registry to ensure
    uniqueness across the OpenAPI specification.
    """

    def __init__(self, context: 'OpenAPIContext') -> None:
        """Initialize the Operation ID Generator."""
        self.context = context

    def generate(self, endpoint: 'Endpoint', path: str) -> str:
        """
        Generate a unique operation ID for an OpenAPI operation.

        Uses the explicit operation_id from endpoint metadata if available,
        otherwise generates one from the HTTP method and path. The operation ID
        is registered in the registry to ensure uniqueness.
        """
        operation_id = endpoint.metadata.operation_id

        if operation_id is not None:
            self.context.operation_id_registry.register(operation_id)
            return operation_id

        # Generate operation_id from path and method
        tokens = self._tokenize_path(path)
        method = endpoint.metadata.method.lower()
        operation_id = self._build_operation_id(method, tokens)

        self.context.operation_id_registry.register(operation_id)
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
