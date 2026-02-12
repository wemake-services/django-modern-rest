import json
from http import HTTPMethod, HTTPStatus

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.middleware.csrf import get_token
from typing_extensions import override

from django_modern_rest import (
    Body,
    Controller,
    ResponseSpec,
    modify,
    validate,
)
from django_modern_rest.metadata import EndpointMetadata, ResponseSpecProvider
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.security.django_session import DjangoSessionSyncAuth
from django_modern_rest.test import DMRRequestFactory


class _NoExtrasMetadata(EndpointMetadata):
    @override
    def response_spec_providers(self) -> list[type[ResponseSpecProvider]]:
        return []  # do not add any extra specs


class _NoExtrasController(
    Controller[PydanticSerializer],
    Body[dict[str, str]],
):
    auth = (DjangoSessionSyncAuth(),)

    @validate(
        ResponseSpec(return_type=str, status_code=HTTPStatus.OK),
        metadata_cls=_NoExtrasMetadata,
    )
    def post(self) -> HttpResponse:
        return HttpResponse(b'"abc"')

    @modify(metadata_cls=_NoExtrasMetadata)
    def put(self) -> str:
        return 'abc'


@pytest.mark.parametrize('method', [HTTPMethod.POST, HTTPMethod.PUT])
def test_no_extras_metadata(
    dmr_rf: DMRRequestFactory,
    *,
    method: HTTPMethod,
) -> None:
    """Ensures customizing metadata type works."""
    metadata = _NoExtrasController.api_endpoints[str(method)].metadata
    assert metadata.responses.keys() == {HTTPStatus.OK}

    request = dmr_rf.generic(str(method), '/whatever/', data={})
    csrf_token = get_token(request)
    request.META['HTTP_X_CSRFTOKEN'] = csrf_token
    request.COOKIES['csrftoken'] = csrf_token
    request.user = User()

    response = _NoExtrasController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.content), str)
