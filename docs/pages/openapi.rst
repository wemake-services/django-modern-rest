OpenAPI
=======

Semantic schema generation
--------------------------

TODO: explain how responses are fetched from components and auth

Each endpoint might always return ``500`` status code,
it is not listed by default.
If you want to list this response, consider adding
it to the default list of response specs in controller / settings.


Top level API
-------------

.. autofunction:: dmr.openapi.spec.build_schema


.. autoclass:: dmr.openapi.config.OpenAPIConfig
   :members:


Objects
-------

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

.. autoclass:: dmr.openapi.objects.MediaType
   :members:

.. autoclass:: dmr.openapi.objects.OAuthFlow
   :members:

.. autoclass:: dmr.openapi.objects.OAuthFlows
   :members:

.. autoclass:: dmr.openapi.objects.OpenAPI
   :members:

.. autoclass:: dmr.openapi.objects.OpenAPIFormat
   :members:

.. autoclass:: dmr.openapi.objects.OpenAPIType
   :members:

.. autoclass:: dmr.openapi.objects.Operation
   :members:

.. autoclass:: dmr.openapi.objects.Parameter
   :members:

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


Core
----

.. autoclass:: dmr.openapi.core.builder.OpenAPIBuilder
   :members:

.. autoclass:: dmr.openapi.core.context.OpenAPIContext
   :members:

.. autoclass:: dmr.openapi.core.merger.ConfigMerger
   :members:

.. autoclass:: dmr.openapi.core.registry.OperationIdRegistry
   :members:

.. autoclass:: dmr.openapi.core.registry.SchemaRegistry
   :members:


Builders
--------

.. autoclass:: dmr.openapi.builders.OperationBuilder
   :members:

.. autoclass:: dmr.openapi.builders.OperationIDBuilder
   :members:
