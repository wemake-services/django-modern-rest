Public API
==========

Controller
----------

.. autoclass:: dmr.controller.Controller
  :members:
  :exclude-members: controller_validator_cls, endpoint_cls, error_model, settings_validator_cls
  :inherited-members:
  :show-inheritance:


Endpoint
--------

.. autoclass:: dmr.endpoint.Endpoint
  :members:

.. autoclass:: dmr.metadata.EndpointMetadata
  :members:

.. autodecorator:: dmr.endpoint.modify

.. autodecorator:: dmr.endpoint.validate

.. autodecorator:: dmr.endpoint.request_endpoint


Response, headers and cookies
-----------------------------

.. autoclass:: dmr.metadata.ResponseSpecProvider
  :members:

.. autoclass:: dmr.metadata.ResponseSpec
  :members:

.. autoclass:: dmr.metadata.ResponseSpecMetadata
  :members:

.. autoclass:: dmr.metadata.ResponseModification
  :members:

.. autoexception:: dmr.response.APIError
  :members:

.. autofunction:: dmr.response.build_response

.. autoclass:: dmr.headers.HeaderSpec
  :members:

.. autoclass:: dmr.headers.NewHeader
  :members:

.. autoclass:: dmr.cookies.CookieSpec
  :members:

.. autoclass:: dmr.cookies.NewCookie
  :members:

.. autofunction:: dmr.cookies.set_cookies


Validation
----------

.. autoclass:: dmr.validation.ModifyEndpointPayload
  :members:

.. autoclass:: dmr.validation.ValidateEndpointPayload
  :members:


.. _serializer:

Serialization
-------------

.. autoclass:: dmr.serializer.BaseSerializer
  :members:

.. autoclass:: dmr.serializer.BaseEndpointOptimizer
  :members:

.. autoclass:: dmr.endpoint.SerializerContext
  :members:

.. autoclass:: dmr.serializer.BaseSchemaGenerator
  :members:

.. autoclass:: dmr.components.ComponentParserBuilder
  :members:


Routing
-------

.. autoclass:: dmr.routing.Router
  :members:

.. autofunction:: dmr.routing.build_404_handler

.. autofunction:: dmr.routing.build_500_handler

.. autofunction:: dmr.routing.path

.. autoclass:: dmr.routing.URLExternal
  :members:

.. autofunction:: dmr.routing.external_path


Meta mixins
-----------

.. autoclass:: dmr.options_mixins.MetaMixin
  :members:

.. autoclass:: dmr.options_mixins.AsyncMetaMixin
  :members:


Exceptions
----------

.. autoexception:: dmr.exceptions.UnsolvableAnnotationsError
  :members:
  :show-inheritance:

.. autoexception:: dmr.exceptions.EndpointMetadataError
  :members:
  :show-inheritance:

.. autoexception:: dmr.exceptions.DataParsingError
  :members:
  :show-inheritance:

.. autoexception:: dmr.exceptions.RequestSerializationError
  :members:
  :show-inheritance:

.. autoexception:: dmr.exceptions.ResponseSchemaError
  :members:
  :show-inheritance:

.. autoexception:: dmr.exceptions.ValidationError
  :members:
  :show-inheritance:

.. autoexception:: dmr.exceptions.NotAcceptableError
  :members:
  :show-inheritance:

.. autoexception:: dmr.exceptions.NotAuthenticatedError
  :members:
  :show-inheritance:

.. autoexception:: dmr.exceptions.InternalServerError
  :members:
  :show-inheritance:

.. autoexception:: dmr.exceptions.TooManyRequestsError
  :members:
  :show-inheritance:


Utilities
---------

.. autodata:: dmr.types.Json

.. autodata:: dmr.types.EMPTY

.. autoclass:: dmr.types.AnnotationsContext
  :members:

.. autoclass:: dmr.types.TypeVarInference
  :members:


Decorators
----------

.. autofunction:: dmr.decorators.dispatch_decorator

.. autofunction:: dmr.decorators.endpoint_decorator

.. autofunction:: dmr.decorators.wrap_middleware


Testing
-------

.. autoclass:: dmr.test.DMRRequestFactory
  :members:

.. autoclass:: dmr.test.DMRAsyncRequestFactory
  :members:

.. autoclass:: dmr.test.DMRClient
  :members:

.. autoclass:: dmr.test.DMRAsyncClient
  :members:

Auth
~~~~

.. autofunction:: dmr.test.disabled_auth

Throttling
~~~~~~~~~~

.. autofunction:: dmr.test.reduced_throttling

.. autofunction:: dmr.test.assert_throttled

.. autofunction:: dmr.test.assert_throttling

.. autofunction:: dmr.test.assert_async_throttling


Plugins
-------

Pydantic
~~~~~~~~

.. autoclass:: dmr.plugins.pydantic.PydanticSerializer
  :members:

.. autoclass:: dmr.plugins.pydantic.PydanticFastSerializer
  :members:

.. autoclass:: dmr.plugins.pydantic.serializer.PydanticEndpointOptimizer
  :members:

.. autoclass:: dmr.plugins.pydantic.schema.PydanticSchemaGenerator
  :members:

.. autoclass:: dmr.plugins.pydantic.serializer.ToJsonKwargs
  :members:

.. autoclass:: dmr.plugins.pydantic.serializer.ToModelKwargs
  :members:

Msgspec
~~~~~~~

.. autoclass:: dmr.plugins.msgspec.MsgspecSerializer
  :members:

.. autoclass:: dmr.plugins.msgspec.serializer.MsgspecEndpointOptimizer
  :members:

.. autoclass:: dmr.plugins.msgspec.schema.MsgspecSchemaGenerator
  :members:

.. autoclass:: dmr.plugins.msgspec.serializer.ToJsonKwargs
  :members:

.. autoclass:: dmr.plugins.msgspec.serializer.ToModelKwargs
  :members:


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


OpenAPI Core
~~~~~~~~~~~~

.. autoclass:: dmr.openapi.core.merger.ConfigMerger
   :members:

.. autoclass:: dmr.openapi.core.registry.OperationIdRegistry
   :members:

.. autoclass:: dmr.openapi.core.registry.SchemaRegistry
   :members:

.. autoclass:: dmr.openapi.core.registry.SchemaCallback
  :members:


OpenAPI Generators
~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.openapi.generators.ComponentParserGenerator
   :members:

.. autoclass:: dmr.openapi.generators.ResponseGenerator
   :members:

.. autoclass:: dmr.openapi.generators.SchemaGenerator
   :members:

.. autoclass:: dmr.openapi.generators.SecuritySchemeGenerator
   :members:

.. autoclass:: dmr.openapi.generators.OperationIdGenerator
   :members:


Existing OpenAPI views
~~~~~~~~~~~~~~~~~~~~~~

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
