from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import pytest
import schemathesis as st
from django.urls import reverse

from django_test_app.server.wsgi import application

if TYPE_CHECKING:
    from schemathesis.specs.openapi.schemas import OpenApiSchema

_OPENAPI_URL: Final = reverse('openapi:json')
schema = st.pytest.from_fixture('api_schema')


# NOTE: The `db` fixture is required to enable database access.
# When `st.openapi.from_wsgi()` makes a WSGI request, Django's request
# lifecycle triggers database operations.
@pytest.fixture
def api_schema(db: Any) -> 'OpenApiSchema':
    """Load OpenAPI schema as a pytest fixture."""
    return st.openapi.from_wsgi(_OPENAPI_URL, application)


@schema.parametrize()
def test_schema_path_exists(case: st.Case) -> None:
    """Verify that all API paths defined in the OpenAPI schema are exists.

    Validate that each endpoint path from the schema can be called successfully,
    ensuring the schema correctly represents the available API routes.

    Note: This test only verifies that endpoints are reachable and does not
    validate response structure or content.
    """
    assert case.call().status_code != HTTPStatus.NOT_FOUND
