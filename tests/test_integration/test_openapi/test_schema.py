from typing import TYPE_CHECKING

import pytest
import schemathesis as st
import tracecov
from django.conf import LazySettings
from django.urls import reverse
from tracecov.schemathesis import helpers

from django_test_app.server.wsgi import application

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from schemathesis.specs.openapi.schemas import OpenApiSchema


# The `transactional_db` fixture is required to enable database access.
# When `st.openapi.from_wsgi()` makes a WSGI request, Django's request
# lifecycle triggers database operations.
# The `admin_user` fixture is required here so that `JWTAuth` can use
# its credentials (username and password) for authentication.
# This follows the `pytest-django` pattern for creating user fixtures:
# https://github.com/pytest-dev/pytest-django/blob/main/pytest_django/fixtures.py#L483
@pytest.fixture
def api_schema(transactional_db: None, admin_user: 'User') -> 'OpenApiSchema':
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
