import datetime as dt
import inspect
import json
import re
from http import HTTPStatus
from typing import Any, ClassVar, Final, final

import pytest
from django.http import HttpResponse
from inline_snapshot import snapshot

from dmr import Controller
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.security.django_session import concrete_views as session_views
from dmr.security.jwt import concrete_views as jwt_views
from dmr.security.token import concrete_views as token_views
from dmr.test import DMRRequestFactory


@final
class _GreetingController(Controller[PydanticSerializer]):
    greeting: ClassVar[str] = 'hello'

    def get(self) -> str:
        return self.greeting


def _got(attribute_name: str) -> str:
    return re.escape(f'got [{attribute_name!r}] in `as_view()`')


def test_class_only_attributes_are_complete() -> None:
    """Ensures that all public attributes are listed, but instance ones."""
    annotated = set(inspect.get_annotations(Controller))

    assert annotated - {'kwargs'} == Controller.class_only_attributes


@pytest.mark.parametrize(
    'attribute_name',
    sorted(Controller.class_only_attributes),
)
def test_class_only_attribute_in_as_view(*, attribute_name: str) -> None:
    """Ensures that class only attributes are rejected by ``as_view``."""
    with pytest.raises(EndpointMetadataError, match=_got(attribute_name)):
        _GreetingController.as_view(**{attribute_name: None})


def test_class_only_attributes_message() -> None:
    """Ensures that the error message lists all rejected attributes."""
    with pytest.raises(EndpointMetadataError) as exc_info:
        _GreetingController.as_view(throttling=None, auth=None)

    controller_repr = repr(_GreetingController)
    assert str(exc_info.value).startswith(controller_repr)
    assert str(exc_info.value).removeprefix(controller_repr) == snapshot(
        " got ['auth', 'throttling'] in `as_view()`, "
        'but these attributes are only read from the class, '
        'so passing them to `as_view()` has no effect. '
        'Set them as class attributes instead: on a subclass, '
        'or, for a final controller, on a subclass '
        'of the reusable controller it is built on',
    )


def test_instance_attribute_in_as_view(*, dmr_rf: DMRRequestFactory) -> None:
    """Ensures that attributes read from the instance can be passed."""
    request = dmr_rf.get('/whatever/')

    response = _GreetingController.as_view(greeting='hi')(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert json.loads(response.content) == snapshot('hi')


_CONCRETE_VIEWS_STATUS_CODE: Final = (
    jwt_views.ObtainTokensSyncController,
    jwt_views.CookieObtainTokensSyncController,
    token_views.ObtainTokenSyncController,
    session_views.DjangoSessionSyncController,
)


@pytest.mark.parametrize('controller_cls', _CONCRETE_VIEWS_STATUS_CODE)
@pytest.mark.parametrize(
    'initkwargs',
    [
        {'throttling': None},
        {'response_status_code': HTTPStatus.CREATED},
    ],
)
def test_auth_views_class_only_attributes(
    *,
    controller_cls: Any,
    initkwargs: dict[str, Any],
) -> None:
    """Ensures that auth views reject their own class only attributes."""
    with pytest.raises(EndpointMetadataError, match=_got(*initkwargs)):
        controller_cls.as_view(serializer=PydanticSerializer, **initkwargs)


@pytest.mark.parametrize(
    'attribute_name',
    [
        'jwt_access_cookie',
        'jwt_access_cookie_path',
        'jwt_cookie_secure',
        'jwt_expiration',
        'jwt_refresh_expiration',
    ],
)
def test_cookie_views_class_only_attributes(*, attribute_name: str) -> None:
    """Ensures that cookie settings can't be passed to ``as_view``."""
    initkwargs: dict[str, Any] = {attribute_name: None}
    with pytest.raises(EndpointMetadataError, match=_got(attribute_name)):
        jwt_views.CookieObtainTokensSyncController.as_view(
            serializer=PydanticSerializer,
            **initkwargs,
        )


def test_jwt_body_views_instance_attributes() -> None:
    """Ensures that jwt settings can still be passed to body views."""
    view = jwt_views.ObtainTokensSyncController.as_view(
        serializer=PydanticSerializer,
        jwt_expiration=dt.timedelta(hours=1),
    )

    assert callable(view)


def test_cookie_views_typed_arguments() -> None:
    """Ensures that typed ``as_view`` arguments still work."""
    view = jwt_views.CookieObtainTokensSyncController.as_view(
        serializer=PydanticSerializer,
        jwt_refresh_cookie_path='/api/auth/refresh/',
    )

    assert view.view_class.jwt_refresh_cookie_path == '/api/auth/refresh/'  # type: ignore[attr-defined]
