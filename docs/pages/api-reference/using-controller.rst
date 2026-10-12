Using controllers
=================

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

.. autofunction:: dmr.endpoint.request_endpoint

Modify
~~~~~~

.. autoclass:: dmr.endpoint.ModifyEndpoint
  :members:

.. autodata:: dmr.endpoint.modify

Validate
~~~~~~~~

.. autoclass:: dmr.endpoint.ValidateEndpoint
  :members:

.. autodata:: dmr.endpoint.validate

Extras
~~~~~~

.. autoclass:: dmr.endpoint.Extras
  :members:

Lazy endpoints
~~~~~~~~~~~~~~

.. autoclass:: dmr.endpoint.ModifySyncCallable
  :members:

.. autoclass:: dmr.endpoint.ModifyAsyncCallable
  :members:

.. autoclass:: dmr.endpoint.ModifyAnyCallable
  :members:

.. autoclass:: dmr.endpoint.ValidateSyncCallable
  :members:

.. autoclass:: dmr.endpoint.ValidateAsyncCallable
  :members:

.. autoclass:: dmr.endpoint.ValidateAnyCallable
  :members:

Meta mixins
-----------

.. autoclass:: dmr.options_mixins.MetaMixin
  :members:

.. autoclass:: dmr.options_mixins.AsyncMetaMixin
  :members:
