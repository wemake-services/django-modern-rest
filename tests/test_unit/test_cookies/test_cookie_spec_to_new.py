import dataclasses

import pytest

from dmr import CookieSpec, NewCookie


@pytest.mark.parametrize(
    'spec',
    [
        CookieSpec(),
        CookieSpec(httponly=True, secure=True, samesite='strict'),
        CookieSpec(path='/auth/refresh', max_age=1000, domain='example.com'),
        CookieSpec(description='Some cookie', required=False),
        CookieSpec(skip_validation=True),
    ],
)
def test_to_new_copies_every_cookie_attribute(spec: CookieSpec) -> None:
    """A cookie built from a spec must describe exactly that spec."""
    new_cookie = spec.to_new('some-value')

    assert new_cookie.value == 'some-value'
    for field in dataclasses.fields(NewCookie):
        if field.name == 'value':
            continue
        assert getattr(new_cookie, field.name) == getattr(spec, field.name)


def test_to_new_is_the_inverse_of_to_spec() -> None:
    """``to_spec`` and ``to_new`` must be symmetrical."""
    spec = CookieSpec(httponly=True, secure=True, max_age=1000)

    assert spec.to_new('some-value').to_spec() == spec


def test_to_new_drops_documentation_only_fields() -> None:
    """Fields that are not part of the cookie spec cannot be set on a cookie."""
    spec = CookieSpec(
        description='Some cookie',
        required=False,
        skip_validation=True,
        httponly=True,
    )

    new_cookie = spec.to_new('some-value')

    assert not hasattr(new_cookie, 'description')
    assert not hasattr(new_cookie, 'required')
    assert not hasattr(new_cookie, 'skip_validation')
    assert new_cookie.httponly
