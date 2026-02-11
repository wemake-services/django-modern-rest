from typing import TYPE_CHECKING, Any, Final

import pytest
import schemathesis as st
from django.urls import reverse

from django_test_app.server.wsgi import application

if TYPE_CHECKING:
    from schemathesis.specs.openapi.schemas import OpenApiSchema

_OPENAPI_URL: Final = reverse('openapi:json')
schema = st.pytest.from_fixture('api_schema').exclude(
    # This example must be readable, not correct:
    path=reverse('api:model_examples:user_model_create'),
)


# NOTE: The `db` fixture is required to enable database access.
# When `st.openapi.from_wsgi()` makes a WSGI request, Django's request
# lifecycle triggers database operations.
@pytest.fixture
def api_schema(db: Any) -> 'OpenApiSchema':
    """Load OpenAPI schema as a pytest fixture."""
    return st.openapi.from_wsgi(_OPENAPI_URL, application)


@schema.parametrize()
def test_schemathesis(case: st.Case) -> None:
    """Ensure that API implementation matches the OpenAPI schema."""
    case.call_and_validate()
