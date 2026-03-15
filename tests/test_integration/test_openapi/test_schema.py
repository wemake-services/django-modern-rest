import pytest
import schemathesis as st
from django.conf import LazySettings
from django.urls import reverse
from schemathesis.specs.openapi.schemas import OpenApiSchema

from django_test_app.server.wsgi import application


# NOTE: The `db` fixture is required to enable database access.
# When `st.openapi.from_wsgi()` makes a WSGI request, Django's request
# lifecycle triggers database operations.
@pytest.fixture
def api_schema(db: None) -> 'OpenApiSchema':
    """Load OpenAPI schema as a pytest fixture."""
    return st.openapi.from_wsgi(reverse('openapi'), application)


schema = st.pytest.from_fixture('api_schema')


@schema.parametrize()
def test_schemathesis(case: st.Case, settings: LazySettings) -> None:
    """Ensure that API implementation matches the OpenAPI schema."""
    if settings.DEBUG:
        pytest.skip(
            reason=(
                'Django with DEBUG=True and schemathesis are hard to integrate'
            ),
        )

    case.call_and_validate()
