import uuid
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.headers import HeaderDescription
from django_modern_rest.metadata import EndpointMetadata
from django_modern_rest.openapi.generator.new_collector import ControllerInfo
from django_modern_rest.openapi.objects.header import Header
from django_modern_rest.openapi.objects.operation import Operation
from django_modern_rest.openapi.objects.path_item import PathItem
from django_modern_rest.openapi.objects.reference import Reference
from django_modern_rest.openapi.objects.response import Response
from django_modern_rest.openapi.objects.responses import Responses
from django_modern_rest.response import ResponseDescription
from django_modern_rest.types import Empty


class PathItemFactory:
    def __init__(self, info: ControllerInfo) -> None:
        self.info = info
        self._path_item = PathItem()

    def create(self) -> PathItem:
        for method, endpoint in self.info.controller.api_endpoints.items():
            operation = create_operation(endpoint)
            setattr(self._path_item, method.lower(), operation)

        return self._path_item


def create_operation(endpoint: Endpoint) -> Operation:
    metadata = endpoint.metadata
    return Operation(
        operation_id=create_operation_id(metadata),
        parameters=create_parameters(metadata),
        request_body=create_request_body(metadata),
        responses=create_responses(metadata),
    )


def create_operation_id(metadata: EndpointMetadata):
    return str(uuid.uuid4().hex)


def create_parameters(metadata: EndpointMetadata):
    return None


def create_request_body(metadata: EndpointMetadata):
    return None


def create_responses(metadata: EndpointMetadata) -> Responses:
    responses: Responses = {}

    for method, response_description in metadata.responses.items():
        responses[str(method)] = create_response(response_description)

    return responses


def create_response(response_description: ResponseDescription) -> Response:
    return Response(
        description='test',
        headers=create_headers(response_description.headers),
    )


def create_headers(headers: dict[str, HeaderDescription] | Empty) -> dict[str, Header | Reference] | None:
    if isinstance(headers, Empty):
        return

    _headers: dict[str, Header | Reference] = {}

    for header, description in headers.items():
        _headers[header] = Header(required=description.required)

    return _headers


def gen_pathitems(controllers_info: list[ControllerInfo]) -> list[PathItem]:
    return [PathItemFactory().create(info) for info in controllers_info]
