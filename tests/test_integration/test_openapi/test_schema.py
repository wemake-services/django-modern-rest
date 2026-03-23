import pytest
import schemathesis as st
import tracecov
from django.conf import LazySettings
from django.urls import reverse
from schemathesis.specs.openapi.schemas import OpenApiSchema
from tracecov.schemathesis import helpers

from django_test_app.server.wsgi import application


# The `db` fixture is required to enable database access.
# When `st.openapi.from_wsgi()` makes a WSGI request, Django's request
# lifecycle triggers database operations.
@pytest.fixture
def api_schema(db: None) -> 'OpenApiSchema':
    """Load OpenAPI schema as a pytest fixture."""
    return st.openapi.from_wsgi(reverse('openapi'), application)


schema = st.pytest.from_fixture('api_schema')


@schema.parametrize()
def test_schemathesis(
    case: st.Case,
    settings: LazySettings,
    tracecov_map: tracecov.CoverageMap,
) -> None:
    """Ensure that API implementation matches the OpenAPI schema."""
    if settings.DEBUG:
        pytest.skip(
            reason=(
                'Django with DEBUG=True and schemathesis are hard to integrate'
            ),
        )

    response = case.call_and_validate()
    # Record interaction for `tracecov` report:
    tracecov_map.record_schemathesis_interactions(
        case.method,
        case.operation.full_path,
        [helpers.from_response(case.method, response)],
    )
