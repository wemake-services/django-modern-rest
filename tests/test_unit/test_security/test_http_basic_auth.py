import pytest
from inline_snapshot import snapshot

from django_modern_rest.openapi.objects.components import Components
from django_modern_rest.security.http import (
    HttpBasicAsyncAuth,
    HttpBasicSyncAuth,
)


@pytest.mark.parametrize('typ', [HttpBasicSyncAuth, HttpBasicAsyncAuth])
def test_schema(typ: type[HttpBasicSyncAuth] | type[HttpBasicAsyncAuth]) -> None:
    """Ensures that security scheme is correct for http basic auth."""
    instance = typ()
    scheme = instance.security_scheme

    assert isinstance(scheme, Components)
    assert scheme.security_schemes
    assert len(scheme.security_schemes) == 1
    assert instance.security_requirement == snapshot({'http_basic': []})
