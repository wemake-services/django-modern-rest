"""Performance benchmarks for django-modern-rest (dmr)."""

import datetime as dt
import decimal
import json
import uuid
from contextlib import suppress

import msgspec
import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory
from django.urls import Resolver404, include
from django.urls.resolvers import RegexPattern, URLResolver

from benchmarks.apps.dmr import UserCreateModel, UserModel
from dmr import Body, Controller
from dmr.plugins.msgspec import MsgspecSerializer
from dmr.routing import path as dmr_path

# ---------------------------------------------------------------------------
# Payload used across benchmarks
# ---------------------------------------------------------------------------

_BALANCE = (
    '25666721506226402257037984603520132713'
    '71090937115423072705094165554168535293'
    '122281875947436.27873348719931904401196'
    '72978162105102902366981419'
)

PAYLOAD = {
    'email': 'plvpjyvbLgTVEocDJZie',
    'age': 8090,
    'height': 856016.168063173,
    'average_score': -2.26325427111858,
    'balance': _BALANCE,
    'skills': [
        {
            'name': 'PxDeAhcALzYtmxofdwIJ',
            'description': 'vQxCKSafEyNmWPEbWYkl',
            'optional': True,
            'level': 'starter',
        },
        {
            'name': 'BcOffcGYMqfWXzkbrGHF',
            'description': 'cLyJctuAPYTngCIvGkBf',
            'optional': False,
            'level': 'pro',
        },
    ],
    'aliases': {
        'dVcUntdsXjVryBIxJvFc': 'gLNAiWuqSzjtIMQKeuuX',
        'uxdzUXEimvizGhcWWKFf': 0,
    },
    'birthday': '2023-06-07T07:39:06.721384',
    'timezone_diff': 'P0D',
    'friends': [],
    'best_friend': None,
    'promocodes': [
        '3d2656e9-14cc-47b9-b2f4-4056fa55c282',
    ],
    'items': [
        {
            'name': 'cXqVPuSCmNfxKOmZmcUI',
            'quality': 3783,
            'count': 4861,
            'rarety': 5450,
            'parts': [],
        },
    ],
}

PAYLOAD_BYTES = json.dumps(PAYLOAD).encode()


@pytest.fixture
def request_factory():
    return RequestFactory()


# ---------------------------------------------------------------------------
# URL Resolver benchmarks
# ---------------------------------------------------------------------------


def _a_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse(b'')


def _build_resolver() -> URLResolver:
    inner_patterns = [
        dmr_path('users/', _a_view),
        dmr_path('users/<int:user_id>', _a_view),
        dmr_path('users/<int:user_id>/posts', _a_view),
        dmr_path(
            'users/<int:user_id>/posts/<int:post_id>',
            _a_view,
        ),
        dmr_path('articles/', _a_view),
        dmr_path('articles/<slug:slug>', _a_view),
        dmr_path('articles/<slug:slug>/comments', _a_view),
        dmr_path('authors/', _a_view),
        dmr_path('authors/<int:author_id>', _a_view),
        dmr_path('categories/', _a_view),
        dmr_path('categories/<slug:category_slug>', _a_view),
        dmr_path('tags/', _a_view),
        dmr_path('tags/<str:tag_name>', _a_view),
        dmr_path('products/', _a_view),
        dmr_path('products/<int:product_id>', _a_view),
        dmr_path('products/<int:product_id>/reviews', _a_view),
        dmr_path(
            'products/<int:product_id>/reviews/<int:review_id>',
            _a_view,
        ),
        dmr_path('orders/', _a_view),
        dmr_path('orders/<uuid:order_id>', _a_view),
        dmr_path('payments/', _a_view),
        dmr_path('payments/<uuid:payment_id>', _a_view),
        dmr_path('inventory/', _a_view),
        dmr_path('inventory/<int:item_id>', _a_view),
        dmr_path('suppliers/', _a_view),
        dmr_path('suppliers/<int:supplier_id>', _a_view),
        dmr_path('customers/', _a_view),
        dmr_path('customers/<int:customer_id>', _a_view),
        dmr_path('addresses/', _a_view),
        dmr_path('addresses/<int:address_id>', _a_view),
        dmr_path('notifications/', _a_view),
        dmr_path(
            'notifications/<int:notification_id>',
            _a_view,
        ),
        dmr_path('settings/', _a_view),
        dmr_path('settings/<str:key>', _a_view),
        dmr_path('analytics/', _a_view),
        dmr_path('analytics/<str:metric>', _a_view),
        dmr_path('reports/', _a_view),
        dmr_path('reports/<int:report_id>', _a_view),
        dmr_path('audit/', _a_view),
        dmr_path('audit/<str:audit_id>', _a_view),
        dmr_path('health', _a_view),
        dmr_path('metrics', _a_view),
    ]
    return URLResolver(
        RegexPattern(r''),
        [
            dmr_path(
                'api/',
                include(
                    (inner_patterns, 'app-name'),
                    namespace='api',
                ),
            ),
        ],
    )


_resolver = _build_resolver()


@pytest.mark.benchmark
def test_url_resolve_best_case(benchmark):
    """Resolve the first URL pattern (best case)."""

    @benchmark
    def _():
        _resolver.resolve('api/users/')


@pytest.mark.benchmark
def test_url_resolve_average_case(benchmark):
    """Resolve a URL pattern in the middle (average case)."""

    @benchmark
    def _():
        _resolver.resolve('api/tags/sometag')


@pytest.mark.benchmark
def test_url_resolve_worst_case(benchmark):
    """Resolve a non-existent URL (worst case, triggers 404)."""

    @benchmark
    def _():
        with suppress(Resolver404):
            _resolver.resolve('api/no-such-path/')


# ---------------------------------------------------------------------------
# Serialization benchmarks (msgspec)
# ---------------------------------------------------------------------------

_body_decoder = msgspec.json.Decoder(UserCreateModel)


@pytest.mark.benchmark
def test_msgspec_body_decode(benchmark):
    """Decode a JSON payload using msgspec."""

    @benchmark
    def _():
        _body_decoder.decode(PAYLOAD_BYTES)


_user_for_encode = UserModel(
    uid=uuid.UUID('fb075379-1372-41e9-ae1f-390802ced0e7'),
    email='test@example.com',
    age=30,
    height=180.5,
    average_score=95.0,
    balance=decimal.Decimal('1000.50'),
    skills=[],
    aliases={},
    birthday=dt.datetime(2023, 6, 7, 7, 39, 6, 721384, tzinfo=dt.UTC),
    timezone_diff=dt.timedelta(0),
    friends=[],
    best_friend=None,
    promocodes=[uuid.UUID('3d2656e9-14cc-47b9-b2f4-4056fa55c282')],
    items=[],
)
_response_encoder = msgspec.json.Encoder()


@pytest.mark.benchmark
def test_msgspec_response_encode(benchmark):
    """Encode a response model to JSON using msgspec."""

    @benchmark
    def _():
        _response_encoder.encode(_user_for_encode)


# ---------------------------------------------------------------------------
# Request handling benchmarks (sync controller via RequestFactory)
# ---------------------------------------------------------------------------


class _SimpleBody(msgspec.Struct):
    email: str
    age: int


class _SimpleResponse(msgspec.Struct):
    uid: uuid.UUID
    email: str
    age: int


class _SimpleController(Controller[MsgspecSerializer]):
    def post(
        self,
        parsed_body: Body[_SimpleBody],
    ) -> _SimpleResponse:
        """Create a simple user response."""
        return _SimpleResponse(
            uid=uuid.UUID('fb075379-1372-41e9-ae1f-390802ced0e7'),
            email=parsed_body.email,
            age=parsed_body.age,
        )


_simple_payload = json.dumps({'email': 'test@example.com', 'age': 30}).encode()
_simple_view = _SimpleController.as_view()


@pytest.mark.benchmark
def test_sync_controller_post(benchmark, request_factory):
    """Full sync POST request through a dmr controller."""

    @benchmark
    def _():
        req = request_factory.post(
            '/user/',
            data=_simple_payload,
            content_type='application/json',
        )
        response = _simple_view(req)
        assert response.status_code == 201
