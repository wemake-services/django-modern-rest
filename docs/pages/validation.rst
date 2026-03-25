Validation
==========

``django-modern-rest`` has several layers of import-time and runtime validation.
We try to do everything that we can during import-time,
so it won't affect your requests and responses.

However, we have to validate requests and responses during the runtime.
Responses validation can be :ref:`turned off <response_validation>`
in production for speed.

What do we validate and how?


.. _settings_validation:

Settings validation
-------------------

We start with settings validation.
We only validate settings once per application,
we do it when the first :class:`~dmr.controller.Controller` is created.

.. autoclass:: dmr.validation.settings.SettingsValidator
  :members:

We also validate our own default values to be correct.


Endpoint validation
-------------------

Next, when controller is being created,
we run :class:`~dmr.endpoint.Endpoint` validation.

Here we can detect all kinds of problems with how endpoints are defined:

- Invalid :func:`~dmr.endpoint.modify`
  or :func:`~dmr.endpoint.validate` usage
- Or invalid :class:`~dmr.settings.HttpSpec` usage

HttpSpec validation
~~~~~~~~~~~~~~~~~~~

You can customize the strictness of HTTP Spec validation with overriding
disabled :class:`~dmr.settings.HttpSpec` options per-endpoint,
per-controller, and globally.

.. warning::

  We don't recommend overriding any of this settings by default.
  It only makes sense to change, when implementing some
  old legacy API the "same" way as it used to be.

  And only you need this for a very specific reason.

.. tabs::

    .. tab:: :octicon:`checklist` The right way

      .. literalinclude:: /examples/validation/httpspec/right_way.py
        :caption: views.py
        :language: python
        :linenos:

    .. tab:: Per endpoint

      .. literalinclude:: /examples/validation/httpspec/per_endpoint.py
        :language: python
        :caption: views.py
        :linenos:
        :emphasize-lines: 11

    .. tab:: Per controller

      .. literalinclude:: /examples/validation/httpspec/per_controller.py
        :language: python
        :caption: views.py
        :linenos:
        :emphasize-lines: 9


.. autoclass:: dmr.validation.endpoint_metadata.EndpointMetadataBuilder

.. autoclass:: dmr.validation.endpoint_metadata.EndpointMetadataValidator


Controller validation
---------------------

The last step is the final :class:`~dmr.controller.Controller`
validation which has everything ready:

- :attr:`~dmr.controller.Controller.api_endpoints`

Here we validate:

- That all ``Controller`` classes have unique methods
- That all endpoints are either sync or async
- All per-controller and per-endpoint error handling

.. autoclass:: dmr.validation.controller.ControllerValidator
  :members:


Response validation
-------------------

The last step is to validate the response when returning
it from the endpoint in runtime.
We need this to make sure that API responses always match response schemas.

It can be :ref:`turned off <response_validation>`.

.. autoclass:: dmr.validation.response.ResponseValidator
  :members:

.. autoclass:: dmr.validation.response.ValidatedModification
  :members:
