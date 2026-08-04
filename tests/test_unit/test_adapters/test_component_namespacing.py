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
    """Plain Django view imported from a foreign specification."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Build the report the way plain Django would."""
        return HttpResponse(b'{}', content_type='application/json')


class _ProjectExportView(View):
    """Plain Django view of our own, described without a prefix."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Export the report the way plain Django would."""
        return HttpResponse(b'id,name', content_type='text/csv')


_REPORT_PATH_ITEM = objects.PathItem(
    get=objects.Operation(
        summary='Build a report',
        parameters=[objects.Reference(ref='#/components/parameters/Format')],
        request_body=objects.Reference(
            ref='#/components/requestBodies/Filter',
        ),
        responses={
            '200': objects.Reference(ref='#/components/responses/Built'),
        },
    ),
)

# `ErrorModel` is also the name of a schema the framework generates,
# so it only survives here because the contribution is namespaced.
_REPORT_COMPONENTS = objects.Components(
    schemas={
        'ErrorModel': objects.Schema(
            type=OpenAPIType.OBJECT,
            properties={'since': objects.Schema(type=OpenAPIType.STRING)},
        ),
    },
    parameters={
        'Format': objects.Parameter(
            name='format',
            param_in='query',
            schema=objects.Schema(type=OpenAPIType.STRING),
            examples={
                'csv': objects.Reference(ref='#/components/examples/Csv'),
            },
        ),
    },
    examples={'Csv': objects.Example(summary='Comma separated', value='csv')},
    request_bodies={
        'Filter': objects.RequestBody(
            content={
                'application/json': objects.MediaType(
                    schema=objects.Reference(
                        ref='#/components/schemas/ErrorModel',
                    ),
                ),
            },
        ),
    },
    responses={'Built': objects.Response(description='The built report')},
)

# The very same components, spelled the way an OpenAPI document spells them.
# Defaults are explicit here because typed objects always emit them.
_RAW_REPORT_COMPONENTS = MappingProxyType({
    'schemas': {
        'ErrorModel': {
            'type': 'object',
            'properties': {'since': {'type': 'string'}},
        },
    },
    'parameters': {
        'Format': {
            'name': 'format',
            'in': 'query',
            'schema': {'type': 'string'},
            'examples': {'csv': {'$ref': '#/components/examples/Csv'}},
            'deprecated': False,
        },
    },
    'examples': {'Csv': {'summary': 'Comma separated', 'value': 'csv'}},
    'requestBodies': {
        'Filter': {
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/ErrorModel'},
                },
            },
            'required': True,
        },
    },
    'responses': {'Built': {'description': 'The built report'}},
})

_EXPORT_PATH_ITEM = objects.PathItem(
    get=objects.Operation(
        summary='Export a report',
        responses={
            '200': objects.Reference(ref='#/components/responses/Exported'),
        },
    ),
)

_EXPORT_COMPONENTS = objects.Components(
    responses={'Exported': objects.Response(description='The exported report')},
)

_TypedReport = adapt_django_view(
    _LegacyReportView,
    openapi=_REPORT_PATH_ITEM,
    components=_REPORT_COMPONENTS,
    component_prefix='Legacy',
)
_RawReport = adapt_django_view(
    _LegacyReportView,
    openapi=_REPORT_PATH_ITEM,
    components=_RAW_REPORT_COMPONENTS,
    component_prefix='Legacy',
)
_OtherReport = adapt_django_view(
    _LegacyReportView,
    openapi=_REPORT_PATH_ITEM,
    components=_REPORT_COMPONENTS,
    component_prefix='Vendor',
)
_Export = adapt_django_view(
    _ProjectExportView,
    openapi=_EXPORT_PATH_ITEM,
    components=_EXPORT_COMPONENTS,
)


class _UserModel(pydantic.BaseModel):
    username: str


class _UserController(Controller[PydanticSerializer]):
    def get(self) -> _UserModel:
        raise NotImplementedError


def _build_schema(*urls: Any) -> dict[str, Any]:
    return build_schema(Router('api/', list(urls))).convert()


def test_prefixed_and_unprefixed_components(
    snapshot: SnapshotAssertion,
) -> None:
    """Ensure that namespaced and plain contributions share one document."""
    schema = _build_schema(
        path('report/', _TypedReport.as_view()),
        path('export/', _Export.as_view()),
    )

    assert json.dumps(schema, indent=2) == snapshot


def test_prefixed_document_is_valid() -> None:
    """Ensure that every rewritten reference still resolves."""
    router = Router('api/', [path('report/', _TypedReport.as_view())])

    # Raises when `django-modern-rest[openapi]` is installed and the
    # document is invalid — a dangling reference is what would break here:
    assert build_schema(router).convert(skip_validation=False)


def test_top_level_references_are_prefixed() -> None:
    """Ensure that the path item points at the namespaced components."""
    operation = _build_schema(
        path('report/', _TypedReport.as_view()),
    )['paths']['/api/report/']['get']

    assert operation['parameters'] == [
        {'$ref': '#/components/parameters/LegacyFormat'},
    ]
    assert operation['requestBody'] == {
        '$ref': '#/components/requestBodies/LegacyFilter',
    }
    assert operation['responses'] == {
        '200': {'$ref': '#/components/responses/LegacyBuilt'},
    }


def test_nested_references_are_prefixed() -> None:
    """Ensure that a reference inside another component is rewritten too."""
    components = _build_schema(
        path('report/', _TypedReport.as_view()),
    )['components']

    assert components['parameters']['LegacyFormat']['examples'] == {
        'csv': {'$ref': '#/components/examples/LegacyCsv'},
    }
    assert components['requestBodies']['LegacyFilter']['content'] == {
        'application/json': {
            'schema': {'$ref': '#/components/schemas/LegacyErrorModel'},
        },
    }


def test_raw_components_are_prefixed_alike() -> None:
    """Ensure that both spellings pass through the same namespacing."""
    assert _build_schema(
        path('report/', _RawReport.as_view()),
    ) == _build_schema(path('report/', _TypedReport.as_view()))


def test_prefix_is_caller_supplied() -> None:
    """Ensure that the namespace comes from the caller, not from the adapter."""
    components = _build_schema(
        path('report/', _OtherReport.as_view()),
    )['components']

    assert sorted(components['schemas']) == ['VendorErrorModel']
    assert sorted(components['responses']) == ['VendorBuilt']


def test_project_and_foreign_components_coexist() -> None:
    """Ensure that a shared base name leaves both definitions reachable."""
    schema = _build_schema(
        path('user/', _UserController.as_view()),
        path('report/', _TypedReport.as_view()),
    )
    schemas = schema['components']['schemas']
    generated = _build_schema(
        path('user/', _UserController.as_view()),
    )['components']['schemas']

    assert schemas['ErrorModel'] == generated['ErrorModel']
    assert schemas['LegacyErrorModel'] != generated['ErrorModel']
    assert schemas['LegacyErrorModel']['properties'].keys() == {'since'}


def test_same_view_mounted_twice() -> None:
    """Ensure that re-contributing the same definitions is not a conflict."""
    components = _build_schema(
        path('report/', _TypedReport.as_view()),
        path('legacy/report/', _TypedReport.as_view()),
    )['components']

    assert sorted(components['responses']) == ['LegacyBuilt']


def test_namespacing_does_not_change_dispatch(rf: RequestFactory) -> None:
    """Ensure that namespacing components stays a documentation-only act."""
    report = _TypedReport.as_view()(rf.get('/api/report/'))
    export = _Export.as_view()(rf.get('/api/export/'))

    assert isinstance(report, HttpResponse)
    assert isinstance(export, HttpResponse)
    assert report.status_code == HTTPStatus.OK
    assert report.content == b'{}'
    assert export.status_code == HTTPStatus.OK
    assert export.content == b'id,name'


def test_conflicting_contributions_are_reported() -> None:
    """Ensure that two definitions under one name raise, not overwrite."""
    other = adapt_django_view(
        _ProjectExportView,
        openapi=_EXPORT_PATH_ITEM,
        components=objects.Components(
            responses={'Exported': objects.Response(description='Something')},
        ),
    )

    with pytest.raises(ValueError, match='Exported'):
        _build_schema(
            path('export/', _Export.as_view()),
            path('other/', other.as_view()),
        )


def test_conflict_with_a_generated_schema() -> None:
    """Ensure that a contribution cannot be displaced by a generated schema."""
    unprefixed = adapt_django_view(
        _LegacyReportView,
        openapi=_REPORT_PATH_ITEM,
        components=_REPORT_COMPONENTS,
    )

    with pytest.raises(ValueError, match='ErrorModel'):
        _build_schema(
            path('user/', _UserController.as_view()),
            path('report/', unprefixed.as_view()),
        )


def test_invalid_prefix_is_rejected() -> None:
    """Ensure that a prefix that cannot spell a component name is refused."""
    with pytest.raises(ValueError, match='Legacy/'):
        adapt_django_view(
            _LegacyReportView,
            openapi=_REPORT_PATH_ITEM,
            components=_REPORT_COMPONENTS,
            component_prefix='Legacy/',
        )


def _discriminator_schemas(view: Any) -> Any:
    schema = build_schema(
        Router('api/', [path('pet/', view.as_view())]),
    ).convert(skip_validation=True)
    return schema['components']['schemas']


def test_typed_discriminator_targets_are_prefixed() -> None:
    """Ensure that a discriminator points at the namespaced schemas."""
    pet = adapt_django_view(
        _ProjectExportView,
        openapi=_EXPORT_PATH_ITEM,
        components=objects.Components(
            schemas={
                'Dog': objects.Schema(type=OpenAPIType.OBJECT),
                'Pet': objects.Schema(
                    discriminator=objects.Discriminator(
                        property_name='kind',
                        # Both spellings the specification allows:
                        mapping={
                            'dog': '#/components/schemas/Dog',
                            'puppy': 'Dog',
                        },
                    ),
                ),
            },
            responses=_EXPORT_COMPONENTS.responses,
        ),
        component_prefix='Legacy',
    )

    assert _discriminator_schemas(pet)['LegacyPet']['discriminator'] == {
        'propertyName': 'kind',
        'mapping': {
            'dog': '#/components/schemas/LegacyDog',
            'puppy': 'LegacyDog',
        },
    }


def test_raw_discriminator_targets_are_prefixed() -> None:
    """Ensure that both spellings namespace a discriminator alike."""
    pet = adapt_django_view(
        _ProjectExportView,
        openapi=_EXPORT_PATH_ITEM,
        components={
            'schemas': {
                'Dog': {'type': 'object'},
                'Pet': {
                    'discriminator': {
                        'propertyName': 'kind',
                        'mapping': {'dog': '#/components/schemas/Dog'},
                    },
                },
            },
            'responses': {'Exported': {'description': 'The exported report'}},
        },
        component_prefix='Legacy',
    )

    assert _discriminator_schemas(pet)['LegacyPet']['discriminator'] == {
        'propertyName': 'kind',
        'mapping': {'dog': '#/components/schemas/LegacyDog'},
    }


def test_discriminator_without_a_mapping() -> None:
    """Ensure that a discriminator naming no schema is left alone."""
    pet = adapt_django_view(
        _ProjectExportView,
        openapi=_EXPORT_PATH_ITEM,
        components=objects.Components(
            schemas={
                'Pet': objects.Schema(
                    discriminator=objects.Discriminator(property_name='kind'),
                ),
            },
        ),
        component_prefix='Legacy',
    )

    assert _discriminator_schemas(pet)['LegacyPet']['discriminator'] == {
        'propertyName': 'kind',
    }


def test_reference_outside_the_categories() -> None:
    """Ensure that the prefix only owns what an adapted view can contribute."""
    header_ref = {'$ref': '#/components/headers/Total'}
    referencing = adapt_django_view(
        _ProjectExportView,
        openapi={
            'get': {
                'responses': {
                    '200': {
                        'description': 'The exported report',
                        'headers': {'X-Total': header_ref},
                    },
                },
            },
        },
        component_prefix='Legacy',
    )

    # A `headers` component cannot be contributed, so the reference is
    # left for the project itself to define, prefix or no prefix:
    schema = build_schema(
        Router('api/', [path('export/', referencing.as_view())]),
    ).convert(skip_validation=True)
    operation = schema['paths']['/api/export/']['get']

    assert operation['responses']['200']['headers'] == {'X-Total': header_ref}


def test_prefix_without_components() -> None:
    """Ensure that the prefix describes the view, not only its components."""
    referencing = adapt_django_view(
        _ProjectExportView,
        openapi=_EXPORT_PATH_ITEM,
        component_prefix='Legacy',
    )
    contributing = adapt_django_view(
        _LegacyReportView,
        openapi=objects.PathItem(),
        components=_EXPORT_COMPONENTS,
        component_prefix='Legacy',
    )

    schema = _build_schema(
        path('export/', referencing.as_view()),
        path('report/', contributing.as_view()),
    )

    assert schema['paths']['/api/export/']['get']['responses'] == {
        '200': {'$ref': '#/components/responses/LegacyExported'},
    }
    assert sorted(schema['components']['responses']) == ['LegacyExported']
