Public API
==========

Controller
----------

.. autoclass:: django_modern_rest.controller.Controller
  :members:
  :exclude-members: endpoint_cls, serializer_context_cls, controller_validator_cls


Endpoint
--------

.. autoclass:: django_modern_rest.endpoint.Endpoint
  :members:

.. autoclass:: django_modern_rest.metadata.EndpointMetadata

.. autofunction:: django_modern_rest.endpoint.modify

.. autofunction:: django_modern_rest.endpoint.validate


Components
----------

.. autoclass:: django_modern_rest.components.Headers

.. autoclass:: django_modern_rest.components.Query

.. autoclass:: django_modern_rest.components.Body


Response and headers
--------------------

.. autoclass:: django_modern_rest.response.ResponseDescription
  :members:

.. autoclass:: django_modern_rest.response.ResponseModification
  :members:

.. autoclass:: django_modern_rest.headers.HeaderDescription
  :members:

.. autoclass:: django_modern_rest.headers.NewHeader
  :members:

.. autodata:: django_modern_rest.headers.ResponseHeadersT


Validation
----------

.. autoclass:: django_modern_rest.validation.ControllerValidator
  :members:

.. autoclass:: django_modern_rest.validation.ResponseValidator

.. autoclass:: django_modern_rest.validation.EndpointMetadataValidator

.. autoclass:: django_modern_rest.validation.ModifyEndpointPayload

.. autoclass:: django_modern_rest.validation.ValidateEndpointPayload


Serialization
-------------

.. autoclass:: django_modern_rest.serialization.BaseSerializer
  :members:

.. autoclass:: django_modern_rest.serialization.SerializerContext


Routing
-------

.. autoclass:: django_modern_rest.routing.Router
  :members:

.. autofunction:: django_modern_rest.routing.compose_controllers


Meta mixins
-----------

.. autoclass:: django_modern_rest.options_mixins.MetaMixin
  :members:

.. autoclass:: django_modern_rest.options_mixins.AsyncMetaMixin
  :members:


Exceptions
----------

.. autoclass:: django_modern_rest.exceptions.UnsolvableAnnotationsError
  :members:

.. autoclass:: django_modern_rest.exceptions.EndpointMetadataError
  :members:

.. autoclass:: django_modern_rest.exceptions.DataParsingError
  :members:

.. autoclass:: django_modern_rest.exceptions.SerializationError
  :members:

.. autoclass:: django_modern_rest.exceptions.RequestSerializationError
  :members:

.. autoclass:: django_modern_rest.exceptions.ResponseSerializationError
  :members:


Utilities
---------

.. autoclass:: django_modern_rest.types.Empty

.. autodata:: django_modern_rest.types.EmptyObj


Decorators
----------

.. autoclass:: django_modern_rest.decorators.dispatch_decorator

.. autoclass:: django_modern_rest.decorators.wrap_middleware


Plugins
-------

.. autoclass:: django_modern_rest.plugins.pydantic.PydanticSerializer

.. autoclass:: django_modern_rest.plugins.msgspec.MsgspecSerializer
