Validation
==========

``django-modern-rest`` has several layers of import-time and runtime validation.
We try to do everything that we can during import-time,
so it won't affect your requests and responses.

However, we have to validate requests and responses during the runtime.
Responses validation can be :ref:`turned off <response_validation>`
in production for speed.

What do we validate and how?


Blueprint validation
--------------------

First layer of validation.

Validates that :class:`~django_modern_rest.controller.Blueprint`
creation is correct by itself. At this early stage blueprints do not have
:class:`endpoints <django_modern_rest.endpoint.Endpoint>` just yet.

So, the things we can validate is very limited.
We would have the full context when you will compose blueprints
into a :class:`~django_modern_rest.controller.Controller`.

You can customize ``Blueprint`` validation via setting
:attr:`~django_modern_rest.controller.Blueprint.blueprint_validator_cls`.

.. autoclass:: django_modern_rest.validation.BlueprintValidator
  :members:


Endpoint validation
-------------------

Next, when controller is being created,
we run :class:`~django_modern_rest.endpoint.Endpoint` validation.

Here we can detect all kinds of problems with how endpoints are defined.

HttpSpec validation
~~~~~~~~~~~~~~~~~~~

You can customize the strictness of HTTP Spec validation with overriding
disabled :class:`~django_modern_rest.settings.HttpSpec` options per-endpoint,
per-blueprint, per-controller and globally.

.. warning::

  We don't recommend overriding any of this settings by default.
  It only makes sense to change, when implementing some
  old legacy API the "same" way as it used to be.

  And only you need this for a very specific reason.

.. tabs::

    .. tab:: :octicon:`checklist` The right way

      .. literalinclude:: /examples/validation/httpspec/right_way.py
        :caption: views.py
        :linenos:

    .. tab:: Per endpoint

      .. literalinclude:: /examples/validation/httpspec/per_endpoint.py
        :language: python
        :caption: views.py
        :linenos:
        :emphasize-lines: 6, 13

    .. tab:: Per blueprint or controller

      .. literalinclude:: /examples/validation/httpspec/per_controller.py
        :language: python
        :caption: views.py
        :linenos:
        :emphasize-lines: 6, 11



Controller validation
---------------------

.. autoclass:: django_modern_rest.validation.ControllerValidator
