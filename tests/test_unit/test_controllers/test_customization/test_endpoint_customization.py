from typing import ClassVar, final

from django_modern_rest import Controller
from django_modern_rest.endpoint import Endpoint
from django_modern_rest.plugins.pydantic import PydanticSerializer


@final
class _EndpointSubclass(Endpoint):
    """Test that we can replace the default implementation."""


@final
class _CustomEndpointController(Controller[PydanticSerializer]):
    endpoint_cls: ClassVar[type[Endpoint]] = _EndpointSubclass

    def get(self) -> int:
        raise NotImplementedError


def test_custom_endpoint_controller() -> None:
    """Ensures we can customize the endpoint factory."""
    assert len(_CustomEndpointController.api_endpoints) == 1
    assert isinstance(
        _CustomEndpointController.api_endpoints['GET'],
        _EndpointSubclass,
    )
