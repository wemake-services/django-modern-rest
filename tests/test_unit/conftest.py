import pytest

with_debug_mode_changed_csrf_failure = pytest.mark.parametrize(
    ('debug_mode', 'expected_csrf_railure_reason'),
    [
        (True, 'CSRF cookie not set.'),
        (False, 'Forbidden.'),
    ],
)
