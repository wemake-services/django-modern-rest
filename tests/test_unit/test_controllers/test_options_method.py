from http import HTTPStatus
from typing_extensions import override

from django.http import HttpResponse
from django_modern_rest import (
    Controller,
    HeaderDescription,
    ResponseDescription,
    validate,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


class _ProblematicController(Controller[PydanticSerializer]):
    """Reproduces the issue from GitHub - shows typing error with @override options."""
    
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


class _NewMetaController(Controller[PydanticSerializer]):
    """Shows new solution with meta method."""
    
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
    def meta(self) -> HttpResponse:  # New solution!
        return self.to_response(
            None,
            status_code=HTTPStatus.NO_CONTENT,
            headers={
                'Allow': ', '.join(['GET', 'OPTIONS']),
            },
        )


def test_options_method_typing_error() -> None:
    """Test shows typing error with @override options method."""
    # This test should show mypy/pyright error when we run type checking
    # The error should be:
    # error: Signature of "options" incompatible with supertype "django.views.generic.base.View"
    pass


def test_meta_method_works(dmr_rf: DMRRequestFactory) -> None:
    """Test shows that meta method works without typing errors."""
    request = dmr_rf.options('/test/')
    response = _NewMetaController.as_view()(request)
    
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response['Allow'] == 'GET, OPTIONS'


def test_default_options_behavior(dmr_rf: DMRRequestFactory) -> None:
    """Test shows automatic OPTIONS behavior."""
    class _SimpleController(Controller[PydanticSerializer]):
        def get(self) -> str:
            return "OK"
        
        def post(self) -> str:
            return "Created"
    
    request = dmr_rf.options('/test/')
    response = _SimpleController.as_view()(request)
    
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert 'GET' in response['Allow']
    assert 'POST' in response['Allow']
    assert 'OPTIONS' in response['Allow']


def test_options_deprecated() -> None:
    """Test shows that options method should be blocked."""
    import warnings
    warnings.simplefilter('always')
    
    class _DeprecatedController(Controller[PydanticSerializer]):
        @validate(ResponseDescription(str, status_code=HTTPStatus.OK))
        def get(self) -> HttpResponse:
            return HttpResponse(b'OK')
    
    controller = _DeprecatedController()
    
    from django.test import RequestFactory
    rf = RequestFactory()
    request = rf.options('/test/')
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            controller.options(request)
        except NotImplementedError as e:
            assert "Please do not use `options` method with `django-modern-rest`" in str(e)
            assert "use `meta` method instead" in str(e)
    
    assert len(w) > 0, "Should have deprecation warning"
    deprecation_warning = w[0]
    warning_text = str(deprecation_warning.message).lower()
    assert "please do not use" in warning_text
    assert "options" in warning_text
    assert "use" in warning_text and "meta" in warning_text
