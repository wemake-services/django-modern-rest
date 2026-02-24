import json
from http import HTTPMethod, HTTPStatus
from typing import Final

import pytest
from django.urls import reverse
from inline_snapshot import snapshot

from dmr.negotiation import ContentType
from dmr.test import DMRClient

_URL: Final = reverse('api:negotiations:negotiation')
_XML_DATA: Final = """<_RequestModel>
  <payment_method_id>card</payment_method_id>
  <payment_amount>big</payment_amount>
</_RequestModel>"""
_XML_EMPTY_DATA: Final = '<_RequestModel></_RequestModel>'
_JSON_DATA: Final = json.dumps({
    'payment_method_id': 'card',
    'payment_amount': 'big',
})


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
    assert response['Content-Type'] == ContentType.json
    assert response.json() == ['card', 'big']


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
    assert response['Content-Type'] == ContentType.xml
    assert response.text == snapshot("""\
<?xml version="1.0" encoding="utf-8"?>
<_RequestModel><payment_method_id>card</payment_method_id><payment_amount>big</payment_amount></_RequestModel>\
""")


@pytest.mark.parametrize('method', [HTTPMethod.POST, HTTPMethod.PUT])
def test_negotiation_empty_xml_to_xml(
    dmr_client: DMRClient,
    *,
    method: HTTPMethod,
) -> None:
    """Test sending XML and receiving empty XML."""
    response = dmr_client.generic(
        str(method),
        _URL,
        data=_XML_EMPTY_DATA,
        headers={
            'Content-Type': str(ContentType.xml),
            'Accept': str(ContentType.xml),
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.content
    assert response['Content-Type'] == ContentType.xml
    assert response.text == snapshot("""\
<?xml version="1.0" encoding="utf-8"?>
<dict><detail><msg>Input should be a valid dictionary \
or instance of _RequestModel</msg><loc>parsed_body</loc>\
<type>value_error</type></detail></dict>\
""")


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
        data=_JSON_DATA,
        headers={
            'Content-Type': str(ContentType.json),
            'Accept': str(ContentType.xml),
        },
    )

    assert response.status_code == HTTPStatus.CREATED, response.content
    assert response['Content-Type'] == ContentType.xml
    assert response.text == snapshot("""\
<?xml version="1.0" encoding="utf-8"?>
<_RequestModel><payment_method_id>card</payment_method_id><payment_amount>big</payment_amount></_RequestModel>\
""")


@pytest.mark.parametrize('method', [HTTPMethod.POST, HTTPMethod.PUT])
def test_negotiation_invalid_xml(
    dmr_client: DMRClient,
    *,
    method: HTTPMethod,
) -> None:
    """Test sending invalid XML."""
    response = dmr_client.generic(
        str(method),
        _URL,
        data='<invalid-xml',
        headers={
            'Content-Type': str(ContentType.xml),
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == snapshot({
        'detail': [
            {'msg': 'unclosed token: line 1, column 0', 'type': 'value_error'},
        ],
    })
