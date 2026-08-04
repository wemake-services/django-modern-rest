import json
from http import HTTPStatus
from types import MappingProxyType
from typing import Any

import pydantic
import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory
from django.urls import path
from django.views import View
from syrupy.assertion import SnapshotAssertion

from dmr import Controller
from dmr.adapters import adapt_django_view
from dmr.openapi import build_schema, objects
from dmr.openapi.objects.enums import OpenAPIType
from dmr.plugins.pydantic import PydanticSerializer
from dmr.routing import Router


class _LegacyReportView(View):
    """Plain Django view whose description references shared components."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Build the report the way plain Django would."""
        return HttpResponse(b'{}', content_type='application/json')


class _LegacyAuditView(View):
    """Second legacy view, contributing components of its own."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Render the audit trail the way plain Django would."""
        return HttpResponse(b'[]', content_type='application/json')


_REPORT_PATH_ITEM = objects.PathItem(
    post=objects.Operation(
        summary='Build a report',
        parameters=[
            objects.Reference(ref='#/components/parameters/ReportFormat'),
        ],
        request_body=objects.Reference(
            ref='#/components/requestBodies/ReportFilter',
        ),
        responses={
            '200': objects.Reference(ref='#/components/responses/ReportBuilt'),
        },
    ),
)

_REPORT_COMPONENTS = objects.Components(
    schemas={
        'ReportFilter': objects.Schema(
            type=OpenAPIType.OBJECT,
            properties={'since': objects.Schema(type=OpenAPIType.STRING)},
        ),
    },
    parameters={
        'ReportFormat': objects.Parameter(
            name='format',
            param_in='query',
            schema=objects.Schema(type=OpenAPIType.STRING),
            examples={
                'csv': objects.Reference(ref='#/components/examples/CsvFormat'),
            },
        ),
    },
    examples={
        'CsvFormat': objects.Example(summary='Comma separated', value='csv'),
    },
    request_bodies={
        'ReportFilter': objects.RequestBody(
            content={
                'application/json': objects.MediaType(
                    schema=objects.Reference(
                        ref='#/components/schemas/ReportFilter',
                    ),
                ),
            },
        ),
    },
    responses={'ReportBuilt': objects.Response(description='The built report')},
)

# The very same components, spelled the way an OpenAPI document spells them.
# Defaults are explicit here because typed objects always emit them.
_RAW_REPORT_COMPONENTS = MappingProxyType({
    'schemas': {
        'ReportFilter': {
            'type': 'object',
            'properties': {'since': {'type': 'string'}},
        },
    },
    'parameters': {
        'ReportFormat': {
            'name': 'format',
            'in': 'query',
            'schema': {'type': 'string'},
            'examples': {'csv': {'$ref': '#/components/examples/CsvFormat'}},
            'deprecated': False,
        },
    },
    'examples': {'CsvFormat': {'summary': 'Comma separated', 'value': 'csv'}},
    'requestBodies': {
        'ReportFilter': {
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/ReportFilter'},
                },
            },
            'required': True,
        },
    },
    'responses': {'ReportBuilt': {'description': 'The built report'}},
})

_AUDIT_PATH_ITEM = objects.PathItem(
    get=objects.Operation(
        summary='Read the audit trail',
        responses={
            '200': objects.Reference(ref='#/components/responses/AuditListed'),
        },
    ),
)

_AUDIT_COMPONENTS = objects.Components(
    schemas={'AuditEntry': objects.Schema(type=OpenAPIType.OBJECT)},
    responses={
        'AuditListed': objects.Response(
            description='The audit trail',
            content={
                'application/json': objects.MediaType(
                    schema=objects.Reference(
                        ref='#/components/schemas/AuditEntry',
                    ),
                ),
            },
        ),
    },
)

_TypedReport = adapt_django_view(
    _LegacyReportView,
    openapi=_REPORT_PATH_ITEM,
    components=_REPORT_COMPONENTS,
)
_RawReport = adapt_django_view(
    _LegacyReportView,
    openapi=_REPORT_PATH_ITEM,
    components=_RAW_REPORT_COMPONENTS,
)
_Audit = adapt_django_view(
    _LegacyAuditView,
    openapi=_AUDIT_PATH_ITEM,
    components=_AUDIT_COMPONENTS,
)


class _UserModel(pydantic.BaseModel):
    username: str


class _UserController(Controller[PydanticSerializer]):
    def get(self) -> _UserModel:
        raise NotImplementedError


def _build_schema(*urls: Any) -> dict[str, Any]:
    return build_schema(Router('api/', list(urls))).convert()


def test_contributed_components(snapshot: SnapshotAssertion) -> None:
    """Ensure that all five component categories reach the document."""
    schema = _build_schema(path('report/', _TypedReport.as_view()))

    assert json.dumps(schema, indent=2) == snapshot


def test_raw_components_match_typed_objects() -> None:
    """Ensure that a mapping and typed objects describe the same components."""
    assert _build_schema(
        path('report/', _RawReport.as_view()),
    ) == _build_schema(path('report/', _TypedReport.as_view()))


def test_contributed_document_is_valid() -> None:
    """Ensure that the document with contributed components validates."""
    router = Router('api/', [path('report/', _TypedReport.as_view())])

    # Raises when `django-modern-rest[openapi]` is installed and the
    # document is invalid — a dangling reference is what would break here:
    assert build_schema(router).convert(skip_validation=False)


def test_components_from_two_views() -> None:
    """Ensure that two adapted views can both contribute components."""
    schema = _build_schema(
        path('report/', _TypedReport.as_view()),
        path('audit/', _Audit.as_view()),
    )
    components = schema['components']

    assert sorted(schema['paths']) == ['/api/audit/', '/api/report/']
    assert sorted(components['schemas']) == ['AuditEntry', 'ReportFilter']
    assert sorted(components['responses']) == ['AuditListed', 'ReportBuilt']
    assert sorted(components['parameters']) == ['ReportFormat']
    assert sorted(components['examples']) == ['CsvFormat']
    assert sorted(components['requestBodies']) == ['ReportFilter']


def test_generated_schemas_are_untouched() -> None:
    """Ensure that contributions do not disturb the framework's own schemas."""
    with_adapter = _build_schema(
        path('user/', _UserController.as_view()),
        path('report/', _TypedReport.as_view()),
    )
    without_adapter = _build_schema(path('user/', _UserController.as_view()))

    generated = without_adapter['components']['schemas']
    assert generated
    assert {
        name: schema
        for name, schema in with_adapter['components']['schemas'].items()
        if name in generated
    } == generated


def test_no_components_without_contributions() -> None:
    """Ensure that a view without components leaves the document alone."""
    plain = adapt_django_view(
        _LegacyAuditView,
        openapi=objects.PathItem(
            get=objects.Operation(
                responses={'200': objects.Response(description='Ok')},
            ),
        ),
    )

    components = _build_schema(
        path('audit/', plain.as_view()),
    )['components']

    assert 'responses' not in components
    assert 'parameters' not in components
    assert 'examples' not in components
    assert 'requestBodies' not in components


def test_contribution_does_not_change_dispatch(rf: RequestFactory) -> None:
    """Ensure that contributing components stays a documentation-only act."""
    report = _TypedReport.as_view()(rf.post('/api/report/'))
    audit = _Audit.as_view()(rf.get('/api/audit/'))

    assert isinstance(report, HttpResponse)
    assert isinstance(audit, HttpResponse)
    assert report.status_code == HTTPStatus.OK
    assert report.content == b'{}'
    assert audit.status_code == HTTPStatus.OK
    assert audit.content == b'[]'


def test_unsupported_raw_category() -> None:
    """Ensure that an unsupported category is reported, not silently dropped."""
    with pytest.raises(TypeError, match='securitySchemes'):
        adapt_django_view(
            _LegacyAuditView,
            openapi=_AUDIT_PATH_ITEM,
            components={'securitySchemes': {'apiKey': {'type': 'apiKey'}}},
        )


def test_unsupported_typed_category() -> None:
    """Ensure that both spellings reject an unsupported category alike."""
    with pytest.raises(TypeError, match='headers'):
        adapt_django_view(
            _LegacyAuditView,
            openapi=_AUDIT_PATH_ITEM,
            components=objects.Components(
                headers={'X-Total-Count': objects.Header()},
            ),
        )
