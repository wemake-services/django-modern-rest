Public API
==========

Controller
----------

.. autoclass:: django_modern_rest.controller.Controller


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


Utilities
---------

.. autoclass:: django_modern_rest.types.Empty

.. autodata:: django_modern_rest.types.EmptyObj

