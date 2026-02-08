import datetime as dt
import secrets
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Final, TypeAlias, final

import pytest
from django.conf import LazySettings
from django.contrib.auth.models import User
from django.http import HttpResponse
from faker import Faker
from freezegun.api import FrozenDateTimeFactory

from django_modern_rest import Controller, modify
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.jwt import JWTSyncAuth, JWTToken
from django_modern_rest.test import DMRRequestFactory


@pytest.fixture
def user(faker: Faker) -> User:
    """Create fake user for tests."""
    return User.objects.create_user(
        faker.user_name(),
        faker.email(),
        faker.password(),
    )


_TokenBuilder: TypeAlias = Callable[..., str]


@pytest.fixture
def build_user_token(user: User, settings: LazySettings) -> _TokenBuilder:
    """Token factory for tests."""

    def factory(**kwargs: Any) -> str:
        return JWTToken(
            sub=str(user.pk),
            exp=kwargs.pop(
                'exp',
                dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            ),
            **kwargs,  # TODO: create a protocol for kwargs
        ).encode(secret=settings.SECRET_KEY, algorithm='HS256')

    return factory


_ISSUER: Final = 'wemake-services/django-modern-rest'


@final
class _IssuerController(Controller[PydanticSerializer]):
    @modify(auth=[JWTSyncAuth(accepted_issuers=_ISSUER)])
    def get(self) -> str:
        return 'authed'


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('issuer', 'response_code'),
    [
        (_ISSUER, HTTPStatus.OK),
        ('wrong', HTTPStatus.UNAUTHORIZED),
    ],
)
def test_issuer_validation(
    dmr_rf: DMRRequestFactory,
    build_user_token: _TokenBuilder,
    *,
    issuer: str,
    response_code: HTTPStatus,
) -> None:
    """Ensures that issuer validation works."""
    token = build_user_token(iss=issuer)
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )

    response = _IssuerController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == response_code


_AUDIENCE: Final = ('dev', 'qa')


@final
class _AudienceController(Controller[PydanticSerializer]):
    @modify(auth=[JWTSyncAuth(accepted_audiences=_AUDIENCE)])
    def get(self) -> str:
        return 'authed'


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('audience', 'response_code'),
    [
        (_AUDIENCE[0], HTTPStatus.OK),
        (_AUDIENCE[1], HTTPStatus.OK),
        ('wrong', HTTPStatus.UNAUTHORIZED),
    ],
)
def test_audience_validation(
    dmr_rf: DMRRequestFactory,
    build_user_token: _TokenBuilder,
    *,
    audience: str,
    response_code: HTTPStatus,
) -> None:
    """Ensures that audience validation works."""
    token = build_user_token(aud=audience)
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )

    response = _AudienceController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == response_code


@final
class _RequireClaimsController(Controller[PydanticSerializer]):
    @modify(auth=[JWTSyncAuth(require_claims=['jti'])])
    def get(self) -> str:
        return 'authed'


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('jti', 'response_code'),
    [
        (secrets.token_hex(), HTTPStatus.OK),
        (None, HTTPStatus.UNAUTHORIZED),
    ],
)
def test_require_claims_validation(
    dmr_rf: DMRRequestFactory,
    build_user_token: _TokenBuilder,
    *,
    jti: str | None,
    response_code: HTTPStatus,
) -> None:
    """Ensures that require_claims validation works."""
    token = build_user_token(jti=jti)
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )

    response = _RequireClaimsController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == response_code


_LEEWAY: Final = 2


@final
class _LeewayController(Controller[PydanticSerializer]):
    @modify(auth=[JWTSyncAuth(leeway=_LEEWAY)])
    def get(self) -> str:
        return 'authed'


@pytest.mark.django_db
@pytest.mark.freeze_time('02-11-2025 10:15:00')
@pytest.mark.parametrize(
    ('seconds', 'response_code'),
    [
        (_LEEWAY - 1, HTTPStatus.OK),
        (_LEEWAY, HTTPStatus.UNAUTHORIZED),
        (_LEEWAY + 1, HTTPStatus.UNAUTHORIZED),
    ],
)
def test_leeway_exp(
    dmr_rf: DMRRequestFactory,
    build_user_token: _TokenBuilder,
    freezer: FrozenDateTimeFactory,
    *,
    seconds: int,
    response_code: HTTPStatus,
) -> None:
    """Ensures that leeway time gap works."""
    token = build_user_token(exp=dt.datetime.now(dt.UTC))
    # Now, go forward into the future for several seconds:
    freezer.tick(delta=seconds)
    # From now on token is expired, let's check that leeway works:
    request = dmr_rf.get(
        '/whatever/',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )

    response = _LeewayController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == response_code


@final
class _CustomHeaderController(Controller[PydanticSerializer]):
    @modify(auth=[JWTSyncAuth(auth_header='X-Api-Auth', auth_scheme='JWT')])
    def get(self) -> str:
        return 'authed'


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('header', 'prefix', 'response_code'),
    [
        ('X-Api-Auth', 'JWT ', HTTPStatus.OK),
        ('X-Api-Auth', 'Bearer ', HTTPStatus.UNAUTHORIZED),
        ('Authorization', 'JWT ', HTTPStatus.UNAUTHORIZED),
        ('Authorization', 'Bearer ', HTTPStatus.UNAUTHORIZED),
    ],
)
def test_custom_jwt_header(
    dmr_rf: DMRRequestFactory,
    build_user_token: _TokenBuilder,
    *,
    header: str,
    prefix: str,
    response_code: HTTPStatus,
) -> None:
    """Ensures that custom header works."""
    token = build_user_token()
    request = dmr_rf.get(
        '/whatever/',
        headers={
            header: prefix + token,
        },
    )

    response = _CustomHeaderController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.headers == {'Content-Type': 'application/json'}
    assert response.status_code == response_code
