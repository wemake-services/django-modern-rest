Public API
==========

Controller
----------

.. autoclass:: dmr.controller.Blueprint
  :members:
  :exclude-members: endpoint_cls, serializer_context_cls, blueprint_validator_cls, controller_validator_cls, settings_validator_cls, error_model
  :show-inheritance:

.. autoclass:: dmr.controller.Controller
  :members:
  :inherited-members:
  :exclude-members: endpoint_cls, serializer_context_cls, blueprint_validator_cls, controller_validator_cls, settings_validator_cls, error_model
  :show-inheritance:


Endpoint
--------

.. autoclass:: dmr.endpoint.Endpoint
  :members:

.. autoclass:: dmr.metadata.EndpointMetadata
  :members:

.. autodecorator:: dmr.endpoint.modify

.. autodecorator:: dmr.endpoint.validate


Response, headers and cookies
-----------------------------

.. autoclass:: dmr.metadata.ResponseSpecProvider
  :members:

.. autoclass:: dmr.metadata.ResponseSpec
  :members:

.. autoclass:: dmr.metadata.ResponseModification
  :members:

.. autoexception:: dmr.response.APIError
  :members:

.. autoexception:: dmr.response.APIRedirectError
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

.. autoclass:: dmr.serializer.SerializerContext
  :members:

.. autoclass:: dmr.serializer.BaseSchemaGenerator
  :members:


Routing
-------

.. autoclass:: dmr.routing.Router
  :members:

.. autofunction:: dmr.routing.compose_blueprints

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

.. autoexception:: dmr.exceptions.EndpointMetadataError
  :members:

.. autoexception:: dmr.exceptions.DataParsingError
  :members:

.. autoexception:: dmr.exceptions.RequestSerializationError
  :members:

.. autoexception:: dmr.exceptions.ResponseSchemaError
  :members:

.. autoexception:: dmr.exceptions.ValidationError
  :members:

.. autoexception:: dmr.exceptions.NotAcceptableError
  :members:

.. autoexception:: dmr.exceptions.NotAuthenticatedError
  :members:

.. autoexception:: dmr.exceptions.InternalServerError
  :members:


Utilities
---------

.. autoclass:: dmr.types.Empty

.. autodata:: dmr.types.EmptyObj


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

.. autoclass:: dmr.plugins.pydantic.serializer.PydanticEndpointOptimizer
  :members:

.. autoclass:: dmr.plugins.pydantic.schema.PydanticSchemaGenerator
  :members:

Msgspec
~~~~~~~

.. autoclass:: dmr.plugins.msgspec.MsgspecSerializer
  :members:

.. autoclass:: dmr.plugins.msgspec.serializer.MsgspecEndpointOptimizer
  :members:

.. autoclass:: dmr.plugins.msgspec.schema.MsgspecSchemaGenerator
  :members:
