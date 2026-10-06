OpenAPI
=======

Schema configuration
--------------------

This is the API every user needs:

.. autofunction:: dmr.openapi.build_schema

.. autoclass:: dmr.openapi.OpenAPIConfig
   :members:

.. autofunction:: dmr.openapi.default_config

.. autoclass:: dmr.openapi.OpenAPIContext
   :members:

.. autofunction:: dmr.openapi.load_schema

Objects and customization hooks are listed in :ref:`openapi-reference`.

.. _openapi-reference:

OpenAPI
-------

Main OpenAPI object:

.. autoclass:: dmr.openapi.openapi.OpenAPI
  :members:

Parts:

.. autoclass:: dmr.openapi.objects.Callback
  :members:

.. autoclass:: dmr.openapi.objects.Components
  :members:

.. autoclass:: dmr.openapi.objects.Contact
  :members:

.. autoclass:: dmr.openapi.objects.Discriminator
  :members:

.. autoclass:: dmr.openapi.objects.Encoding
  :members:

.. autoclass:: dmr.openapi.objects.Example
  :members:

.. autoclass:: dmr.openapi.objects.ExternalDocumentation
  :members:

.. autoclass:: dmr.openapi.objects.Header
  :members:

.. autoclass:: dmr.openapi.objects.Info
  :members:

.. autoclass:: dmr.openapi.objects.License
  :members:

.. autoclass:: dmr.openapi.objects.Link
  :members:

.. autoclass:: dmr.openapi.objects.MediaTypeMetadata
  :members:

.. autoclass:: dmr.openapi.objects.MediaType
  :members:

.. autoclass:: dmr.openapi.objects.OAuthFlow
  :members:

.. autoclass:: dmr.openapi.objects.OAuthFlows
  :members:

.. autoclass:: dmr.openapi.objects.OpenAPIFormat
  :members:

.. autoclass:: dmr.openapi.objects.OpenAPIType
  :members:

.. autoclass:: dmr.openapi.objects.Operation
  :members:

.. autoclass:: dmr.openapi.objects.ParameterMetadata
  :members:

.. autoclass:: dmr.openapi.objects.Parameter
  :inherited-members:
  :show-inheritance:
  :members:

.. autodata:: dmr.openapi.objects.ParameterLocation

.. autoclass:: dmr.openapi.objects.PathItem
  :members:

.. autoclass:: dmr.openapi.objects.Paths
  :members:

.. autoclass:: dmr.openapi.objects.Reference
  :members:

.. autoclass:: dmr.openapi.objects.RequestBody
  :members:

.. autoclass:: dmr.openapi.objects.Response
  :members:

.. autoclass:: dmr.openapi.objects.Responses
  :members:

.. autoclass:: dmr.openapi.objects.Schema
  :members:

.. autoclass:: dmr.openapi.objects.SecurityRequirement
  :members:

.. autoclass:: dmr.openapi.objects.SecurityScheme
  :members:

.. autoclass:: dmr.openapi.objects.Server
  :members:

.. autoclass:: dmr.openapi.objects.ServerVariable
  :members:

.. autoclass:: dmr.openapi.objects.Tag
  :members:

.. autoclass:: dmr.openapi.objects.XML
  :members:

.. autodata:: dmr.openapi.objects.XMLNodeType

OpenAPI Core
------------

.. autoclass:: dmr.openapi.core.merger.ConfigMerger
  :members:

.. autoclass:: dmr.openapi.core.registry.OperationIdRegistry
  :members:

.. autoclass:: dmr.openapi.core.registry.SchemaRegistry
  :members:

.. autoclass:: dmr.openapi.core.registry.SecuritySchemeRegistry
  :members:


OpenAPI Generators
------------------

.. autoclass:: dmr.openapi.generators.ComponentParserGenerator
   :members:

.. autoclass:: dmr.openapi.generators.component_parsers.ConverterSchema
   :members:

.. autoclass:: dmr.openapi.generators.ResponseGenerator
   :members:

.. autoclass:: dmr.openapi.generators.schema.LoadedSchema
   :members:

.. autoclass:: dmr.openapi.generators.SchemaGenerator
   :members:

.. autoclass:: dmr.openapi.generators.SecuritySchemeGenerator
   :members:

.. autoclass:: dmr.openapi.generators.OperationIdGenerator
   :members:

.. autoclass:: dmr.openapi.generators.ParameterGenerator
   :members:


Collectors
----------

.. autoclass:: dmr.openapi.collector.InternalRouteMetadata
  :members:
  :inherited-members:

.. autoclass:: dmr.openapi.collector.ExternalRouteMetadata
  :members:
  :inherited-members:

Views
-----

Existing implementations:

.. autoclass:: dmr.openapi.views.ScalarView
  :members:

.. autoclass:: dmr.openapi.views.SwaggerView
  :members:

.. autoclass:: dmr.openapi.views.RedocView
  :members:

.. autoclass:: dmr.openapi.views.StoplightView
  :members:

.. autoclass:: dmr.openapi.views.OpenAPIJsonView
  :members:

.. autoclass:: dmr.openapi.views.yaml.OpenAPIYamlView
  :members:

Base classes:

.. autoclass:: dmr.openapi.views.base.OpenAPIView
  :members:
