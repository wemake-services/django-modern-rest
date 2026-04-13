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

.. autoclass:: dmr.types.Empty
  :members:

.. autodata:: dmr.types.EmptyObj

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
