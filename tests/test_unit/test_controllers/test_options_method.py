import warnings
from http import HTTPStatus

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from typing_extensions import override

from django_modern_rest import (
    Controller,
    HeaderDescription,
    ResponseDescription,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


class _ProblematicController(Controller[PydanticSerializer]):
    """Reproduces the issue from GitHub - shows typing error with @override."""

    @validate(ResponseDescription(list[str], status_code=HTTPStatus.ACCEPTED))
    def get(self) -> HttpResponse:
        raise NotImplementedError

    @validate(
        ResponseDescription(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            headers={'Allow': HeaderDescription()},
        ),
    )
    @override  # This causes typing error!
    def options(self) -> HttpResponse:  # Wrong signature for Django View
        return self.to_response(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            headers={
                'Allow': ', '.join(
                    sorted(
                        method.upper()
                        for method in self.existing_http_methods()
                    ),
                ),
            },
        )


class _NewOptionsController(Controller[PydanticSerializer]):
    """Shows new solution with options method."""

    @validate(ResponseDescription(str, status_code=HTTPStatus.OK))
    def get(self) -> HttpResponse:
        return HttpResponse(b'OK')

    @validate(
        ResponseDescription(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            headers={'Allow': HeaderDescription()},
        ),
    )
    def options(self) -> HttpResponse:
        return self.to_response(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            headers={
                'Allow': 'GET, OPTIONS',
            },
        )


def test_options_method_works(dmr_rf: DMRRequestFactory) -> None:
    """Test shows that options method works without typing errors."""
    # Debug: check what endpoints are created
    print(f'API endpoints: {list(_NewOptionsController.api_endpoints.keys())}')
    print(
        f'Existing HTTP methods: {_NewOptionsController.existing_http_methods()}'
    )

    request = dmr_rf.options('/test/')
    response = _NewOptionsController.as_view()(request)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response['Allow'] == 'GET, OPTIONS'


def test_options_deprecated() -> None:
    """Test shows that options method should be blocked."""
    warnings.simplefilter('always')

    class _DeprecatedController(Controller[PydanticSerializer]):
        @validate(ResponseDescription(str, status_code=HTTPStatus.OK))
        def get(self) -> HttpResponse:
            return HttpResponse(b'OK')

    controller = _DeprecatedController()

    rf = RequestFactory()
    request = rf.options('/test/')

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        with pytest.raises(NotImplementedError) as exc_info:
            controller.options(request)

        assert (
            'Please do not use `options` method with `django-modern-rest`'
            in str(exc_info.value)
        )
        assert 'define your own `options` method instead' in str(exc_info.value)

    assert len(w) > 0, 'Should have deprecation warning'
    deprecation_warning = w[0]
    warning_text = str(deprecation_warning.message).lower()
    assert 'please do not use' in warning_text
    assert 'options' in warning_text
    assert 'use' in warning_text
