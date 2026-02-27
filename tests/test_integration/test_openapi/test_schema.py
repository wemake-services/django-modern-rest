from typing import TYPE_CHECKING

import pytest
import schemathesis as st
from django.urls import reverse

from django_test_app.server.wsgi import application

if TYPE_CHECKING:
    from schemathesis.specs.openapi.schemas import OpenApiSchema


# NOTE: The `db` fixture is required to enable database access.
# When `st.openapi.from_wsgi()` makes a WSGI request, Django's request
# lifecycle triggers database operations.
@pytest.fixture
def api_schema(db: None) -> 'OpenApiSchema':
    """Load OpenAPI schema as a pytest fixture."""
    return st.openapi.from_wsgi(reverse('openapi'), application)


# TODO: We skip negotiation tests because our implementation of
# XmlParser and XmlRenderer too simple and naive.
schema = st.pytest.from_fixture('api_schema').exclude(
    path='/api/negotiations/negotiation',
)


@schema.parametrize()
def test_schemathesis(case: st.Case) -> None:
    """Ensure that API implementation matches the OpenAPI schema."""
    case.call_and_validate()
