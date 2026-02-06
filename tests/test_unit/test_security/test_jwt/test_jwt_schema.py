import pytest
from inline_snapshot import snapshot

from django_modern_rest.openapi.objects.components import Components
from django_modern_rest.security.jwt import JWTAsyncAuth, JWTSyncAuth


@pytest.mark.parametrize('typ', [JWTSyncAuth, JWTAsyncAuth])
def test_schema(
    typ: type[JWTSyncAuth] | type[JWTAsyncAuth],
) -> None:
    """Ensures that security scheme is correct for jwt auth."""
    instance = typ()
    scheme = instance.security_scheme

    assert isinstance(scheme, Components)
    assert scheme.security_schemes
    assert len(scheme.security_schemes) == 1
    assert instance.security_requirement == snapshot({'jwt': []})
