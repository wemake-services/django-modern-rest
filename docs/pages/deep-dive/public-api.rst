Public API
==========

Controller
----------

.. autoclass:: django_modern_rest.controller.Blueprint
  :members:
  :exclude-members: endpoint_cls, serializer_context_cls, blueprint_validator_cls, controller_validator_cls, error_model
  :show-inheritance:

.. autoclass:: django_modern_rest.controller.Controller
  :members:
  :inherited-members:
  :exclude-members: endpoint_cls, serializer_context_cls, blueprint_validator_cls, controller_validator_cls, error_model
  :show-inheritance:


Endpoint
--------

.. autoclass:: django_modern_rest.endpoint.Endpoint
  :members:

.. autoclass:: django_modern_rest.metadata.EndpointMetadata

.. autodecorator:: django_modern_rest.endpoint.modify

.. autodecorator:: django_modern_rest.endpoint.validate


Response, headers and cookies
-----------------------------

.. autoclass:: django_modern_rest.metadata.ResponseSpecProvider
  :members:

.. autoclass:: django_modern_rest.metadata.ResponseSpec
  :members:

.. autoclass:: django_modern_rest.metadata.ResponseModification
  :members:

.. autoexception:: django_modern_rest.response.APIError
  :members:

.. autoexception:: django_modern_rest.response.APIRedirectError
  :members:

.. autofunction:: django_modern_rest.response.build_response

.. autoclass:: django_modern_rest.headers.HeaderSpec
  :members:

.. autoclass:: django_modern_rest.headers.NewHeader
  :members:

.. autoclass:: django_modern_rest.cookies.CookieSpec
  :members:

.. autoclass:: django_modern_rest.cookies.NewCookie
  :members:


Validation
----------

.. autoclass:: django_modern_rest.validation.ModifyEndpointPayload

.. autoclass:: django_modern_rest.validation.ValidateEndpointPayload


.. _serializer:

Serialization
-------------

.. autoclass:: django_modern_rest.serializer.BaseSerializer
  :members:

.. autoclass:: django_modern_rest.serializer.BaseEndpointOptimizer
  :members:

.. autoclass:: django_modern_rest.serializer.SerializerContext


Routing
-------

.. autoclass:: django_modern_rest.routing.Router
  :members:

.. autofunction:: django_modern_rest.routing.compose_blueprints

.. autofunction:: django_modern_rest.routing.path


Meta mixins
-----------

.. autoclass:: django_modern_rest.options_mixins.MetaMixin
  :members:

.. autoclass:: django_modern_rest.options_mixins.AsyncMetaMixin
  :members:


Exceptions
----------

.. autoexception:: django_modern_rest.exceptions.UnsolvableAnnotationsError
  :members:

.. autoexception:: django_modern_rest.exceptions.EndpointMetadataError
  :members:

.. autoexception:: django_modern_rest.exceptions.DataParsingError
  :members:

.. autoexception:: django_modern_rest.exceptions.RequestSerializationError
  :members:

.. autoexception:: django_modern_rest.exceptions.ResponseSchemaError
  :members:

.. autoexception:: django_modern_rest.exceptions.ValidationError
  :members:

.. autoexception:: django_modern_rest.exceptions.NotAcceptableError
  :members:

.. autoexception:: django_modern_rest.exceptions.NotAuthenticatedError
  :members:

.. autoexception:: django_modern_rest.exceptions.InternalServerError
  :members:


Utilities
---------

.. autoclass:: django_modern_rest.types.Empty

.. autodata:: django_modern_rest.types.EmptyObj


Decorators
----------

.. autofunction:: django_modern_rest.decorators.dispatch_decorator

.. autofunction:: django_modern_rest.decorators.endpoint_decorator

.. autofunction:: django_modern_rest.decorators.wrap_middleware


Testing
-------

.. autoclass:: django_modern_rest.test.DMRRequestFactory

.. autoclass:: django_modern_rest.test.DMRAsyncRequestFactory

.. autoclass:: django_modern_rest.test.DMRClient

.. autoclass:: django_modern_rest.test.DMRAsyncClient


Plugins
-------

.. autoclass:: django_modern_rest.plugins.pydantic.PydanticSerializer

.. autoclass:: django_modern_rest.plugins.msgspec.MsgspecSerializer


Files
-----

.. autoclass:: django_modern_rest.files.FileBody
  :members:


Auth
----

.. autoclass:: django_modern_rest.security.SyncAuth
  :members:
  :inherited-members:

.. autoclass:: django_modern_rest.security.AsyncAuth
  :members:
  :inherited-members:
