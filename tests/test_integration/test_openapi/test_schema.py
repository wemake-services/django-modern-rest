import logging
import os
from collections.abc import Iterator
from typing import TYPE_CHECKING, Final

import pytest
import schemathesis as st
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.urls import reverse
from hypothesis import settings as h_settings
from hypothesis import strategies
from schemathesis.specs.openapi.schemas import OpenApiSchema

from django_test_app.server.wsgi import application
from dmr.validation import ResponseValidator

_LOCAL_MAX_EXAMPLES: Final = 25
_MAX_EXAMPLES: Final = 100 if os.environ.get('CI') else _LOCAL_MAX_EXAMPLES

if TYPE_CHECKING:
    import tracecov


@pytest.fixture(autouse=True)
def _patch_response_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patches the response validator class to never validate the responses,
    # despite their settings. This is needed to test schematesis's
    # response schema validation and compatibility between two. Not ours schema.
    # https://github.com/wemake-services/django-modern-rest/issues/776
    monkeypatch.setattr(
        ResponseValidator,
        '_should_validate_responses',
        lambda *args, **kwargs: False,
    )


@pytest.fixture(autouse=True)
def _disable_logging(settings: LazySettings) -> Iterator[None]:
    # Logging has too much output with schemathesis:
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture(autouse=True)
def _modify_integration_settings(settings: LazySettings) -> None:
    # Schemathesis tests only run meaningfully with DEBUG=False (the test
    # explicitly skips when DEBUG=True), so there is no value in running
    # the full suite twice via the parent conftest parametrisation.
    settings.DEBUG = False


# The `transactional_db` fixture is required to enable database access.
# When `st.openapi.from_wsgi()` makes a WSGI request, Django's request
# lifecycle triggers database operations.
# The `admin_user` fixture is required here so that `JWTAuth` can use
# its credentials (username and password) for authentication.
# This follows the `pytest-django` pattern for creating user fixtures:
# https://github.com/pytest-dev/pytest-django/blob/main/pytest_django/fixtures.py#L483
@pytest.fixture
def api_schema(transactional_db: None, admin_user: User) -> OpenApiSchema:
    """Load OpenAPI schema as a pytest fixture."""
    return st.openapi.from_wsgi(reverse('openapi_json'), application)


schema = st.pytest.from_fixture('api_schema')

# Register custom strategies:
st.openapi.format(
    'phone',
    strategies.from_regex(r'^\+7-495-[0-9]{3}-[0-9]{2}-[0-9]{2}$'),
)


@schema.parametrize()
@h_settings(max_examples=_MAX_EXAMPLES)
def test_schemathesis(
    case: st.Case,
    tracecov_map: 'tracecov.CoverageMap | None',
) -> None:
    """Ensure that API implementation matches the OpenAPI schema."""
    if tracecov_map is None:  # pragma: no cover
        pytest.skip(reason='missing `tracecov`')

    from tracecov.schemathesis import helpers  # noqa: PLC0415

    response = case.call_and_validate()
    # Record interaction for `tracecov` report:
    tracecov_map.record_schemathesis_interactions(
        case.method,
        case.operation.full_path,
        [helpers.from_response(case.method, response)],
    )
