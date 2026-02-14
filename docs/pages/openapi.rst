OpenAPI
=======

Semantic schema generation
--------------------------

TODO: explain how responses are fetched from components and auth

Each endpoint might always return ``500`` status code,
it is not listed by default.
If you want to list this response, consider adding
it to the default list of response specs in controller / settings.


Objects
-------

.. autoclass:: django_modern_rest.openapi.objects.Callback
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Components
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Contact
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Discriminator
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Encoding
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Example
   :members:

.. autoclass:: django_modern_rest.openapi.objects.ExternalDocumentation
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Header
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Info
   :members:

.. autoclass:: django_modern_rest.openapi.objects.License
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Link
   :members:

.. autoclass:: django_modern_rest.openapi.objects.MediaType
   :members:

.. autoclass:: django_modern_rest.openapi.objects.OAuthFlow
   :members:

.. autoclass:: django_modern_rest.openapi.objects.OAuthFlows
   :members:

.. autoclass:: django_modern_rest.openapi.objects.OpenAPI
   :members:

.. autoclass:: django_modern_rest.openapi.objects.OpenAPIFormat
   :members:

.. autoclass:: django_modern_rest.openapi.objects.OpenAPIType
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Operation
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Parameter
   :members:

.. autoclass:: django_modern_rest.openapi.objects.PathItem
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Paths
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Reference
   :members:

.. autoclass:: django_modern_rest.openapi.objects.RequestBody
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Response
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Responses
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Schema
   :members:

.. autoclass:: django_modern_rest.openapi.objects.SecurityRequirement
   :members:

.. autoclass:: django_modern_rest.openapi.objects.SecurityScheme
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Server
   :members:

.. autoclass:: django_modern_rest.openapi.objects.ServerVariable
   :members:

.. autoclass:: django_modern_rest.openapi.objects.Tag
   :members:

.. autoclass:: django_modern_rest.openapi.objects.XML
   :members:


Core
----

.. autoclass:: django_modern_rest.openapi.core.builder.OpenApiBuilder
   :members:

.. autoclass:: django_modern_rest.openapi.core.context.OpenAPIContext
   :members:

.. autoclass:: django_modern_rest.openapi.core.merger.ConfigMerger
   :members:

.. autoclass:: django_modern_rest.openapi.core.registry.OperationIdRegistry
   :members:

.. autoclass:: django_modern_rest.openapi.core.registry.SchemaRegistry
   :members:

.. autoclass:: django_modern_rest.openapi.config.OpenAPIConfig
   :members:

Builders
--------

.. autoclass:: django_modern_rest.openapi.builders.OperationBuilder
   :members:

.. autoclass:: django_modern_rest.openapi.builders.OperationIDBuilder
   :members:
