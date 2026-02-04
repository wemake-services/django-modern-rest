from http import HTTPStatus
from typing import Final

from django.test import Client
from django.urls import reverse

from django_modern_rest.negotiation import ContentType

_URL: Final = reverse('api:negotiations:negotiation')
_XML_DATA = '<root><key>value</key></root>'


def test_negotiation_xml_to_json(client: Client) -> None:
    """Test sending XML and receiving JSON."""
    response = client.post(
        _URL,
        data=_XML_DATA,
        content_type=ContentType.xml,
        HTTP_ACCEPT=ContentType.json,
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == ['value']
    assert response['Content-Type'] == ContentType.json


def test_negotiation_xml_to_xml(client: Client) -> None:
    """Test sending XML and receiving XML."""
    response = client.post(
        _URL,
        data=_XML_DATA,
        content_type=ContentType.xml,
        HTTP_ACCEPT=ContentType.xml,
    )

    assert response.status_code == HTTPStatus.CREATED
    response_content = response.content.decode('utf-8')
    assert '<key>value</key>' in response_content
    assert response['Content-Type'] == ContentType.xml
