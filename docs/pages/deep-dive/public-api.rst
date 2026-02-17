Public API
==========

Controller
----------

.. autoclass:: dmr.controller.Blueprint
  :members:
  :exclude-members: endpoint_cls, serializer_context_cls, blueprint_validator_cls, controller_validator_cls, error_model
  :show-inheritance:

.. autoclass:: dmr.controller.Controller
  :members:
  :inherited-members:
  :exclude-members: endpoint_cls, serializer_context_cls, blueprint_validator_cls, controller_validator_cls, error_model
  :show-inheritance:


Endpoint
--------

.. autoclass:: dmr.endpoint.Endpoint
  :members:

.. autoclass:: dmr.metadata.EndpointMetadata

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

.. autoclass:: dmr.validation.ValidateEndpointPayload


.. _serializer:

Serialization
-------------

.. autoclass:: dmr.serializer.BaseSerializer
  :members:

.. autoclass:: dmr.serializer.BaseEndpointOptimizer
  :members:

.. autoclass:: dmr.serializer.SerializerContext


Routing
-------

.. autoclass:: dmr.routing.Router
  :members:

.. autofunction:: dmr.routing.compose_blueprints

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

.. autoclass:: dmr.test.DMRAsyncRequestFactory

.. autoclass:: dmr.test.DMRClient

.. autoclass:: dmr.test.DMRAsyncClient


Plugins
-------

.. autoclass:: dmr.plugins.pydantic.PydanticSerializer

.. autoclass:: dmr.plugins.msgspec.MsgspecSerializer


Files
-----

.. autoclass:: dmr.files.FileBody
  :members:


Auth
----

.. autoclass:: dmr.security.SyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.AsyncAuth
  :members:
  :inherited-members:
