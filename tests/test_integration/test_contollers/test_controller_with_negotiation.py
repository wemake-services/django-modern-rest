import json
from http import HTTPMethod, HTTPStatus
from typing import Final

import pytest
from django.urls import reverse

from django_modern_rest.negotiation import ContentType
from django_modern_rest.test import DMRClient

_URL: Final = reverse('api:negotiations:negotiation')
_XML_DATA = '<root><key>value</key></root>'


@pytest.mark.parametrize('method', [HTTPMethod.POST, HTTPMethod.PUT])
def test_negotiation_xml_to_json(
    dmr_client: DMRClient,
    *,
    method: HTTPMethod,
) -> None:
    """Test sending XML and receiving JSON."""
    response = dmr_client.generic(
        str(method),
        _URL,
        data=_XML_DATA,
        headers={
            'Content-Type': str(ContentType.xml),
            'Accept': str(ContentType.json),
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response.json() == ['value']
    assert response['Content-Type'] == ContentType.json


@pytest.mark.parametrize('method', [HTTPMethod.POST, HTTPMethod.PUT])
def test_negotiation_xml_to_xml(
    dmr_client: DMRClient,
    *,
    method: HTTPMethod,
) -> None:
    """Test sending XML and receiving XML."""
    response = dmr_client.generic(
        str(method),
        _URL,
        data=_XML_DATA,
        headers={
            'Content-Type': str(ContentType.xml),
            'Accept': str(ContentType.xml),
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    response_content = response.content.decode('utf-8')
    assert '<key>value</key>' in response_content
    assert response['Content-Type'] == ContentType.xml


@pytest.mark.parametrize('method', [HTTPMethod.POST, HTTPMethod.PUT])
def test_negotiation_json_to_xml(
    dmr_client: DMRClient,
    *,
    method: HTTPMethod,
) -> None:
    """Test sending json and receiving XML."""
    response = dmr_client.generic(
        str(method),
        _URL,
        data=json.dumps({'root': {'key': 'value'}}),
        headers={
            'Content-Type': str(ContentType.json),
            'Accept': str(ContentType.xml),
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    response_content = response.content.decode('utf-8')
    assert '<key>value</key>' in response_content
    assert response['Content-Type'] == ContentType.xml
