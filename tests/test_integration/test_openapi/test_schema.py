from collections.abc import Iterator

import pytest
import schemathesis as st
import tracecov  # type: ignore[import-untyped]
from django.urls import reverse
from schemathesis.specs.openapi.schemas import OpenApiSchema
from tracecov.schemathesis import helpers  # type: ignore[import-untyped]

from django_test_app.server.wsgi import application


@pytest.fixture(scope='session')
def coverage_map() -> Iterator[tracecov.CoverageMap]:
    """
    Provide a ``Tracecov`` coverage map for the whole test session.

    The coverage map is initialized from the current schema and is used
    during tests to record which API operations and responses are
    exercised by the test suite. After the tests finishes, a coverage
    report is generated and saved to ``tracecov.json``.
    """
    from django_test_app.server.urls import schema  # noqa: PLC0415

    coverage_map = tracecov.CoverageMap.from_dict(schema.convert())
    yield coverage_map

    coverage_map.save_report(output_file='tracecov.json', format='json')


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
    coverage_map: tracecov.CoverageMap,
) -> None:
    """Ensure that API implementation matches the OpenAPI schema."""
    response = case.call_and_validate()
    # Record interaction for `tracecov` report:
    coverage_map.record_schemathesis_interactions(
        case.method,
        case.operation.full_path,
        [helpers.from_response(case.method, response)],
    )
