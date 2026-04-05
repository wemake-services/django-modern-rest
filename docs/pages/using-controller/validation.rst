.. _response_validation:

Response validation
===================

By default, all responses are validated at runtime to match the schema.
This allows us to be super strict about schema generation as a pro,
but as a con, it is slower than it could possibly be.

You can disable response validation via configuration:

.. warning::

  Disabling response validation makes sense only
  in production for better performance.

  It is not recommended to disable response validation for any other reason.
  Instead, fix your schema errors!

.. tabs::

    .. tab:: Active validation

      .. literalinclude:: /examples/using_controller/active_validation.py
        :caption: views.py
        :language: python
        :linenos:
        :emphasize-lines: 27-33

    .. tab:: Disable per endpoint

      .. literalinclude:: /examples/using_controller/per_endpoint.py
        :caption: views.py
        :language: python
        :linenos:
        :emphasize-lines: 23

    .. tab:: Disable per controller

      .. literalinclude:: /examples/using_controller/per_controller.py
        :caption: views.py
        :language: python
        :linenos:
        :emphasize-lines: 25

    .. tab:: Disable globally

      .. code-block:: python
        :caption: settings.py

        >>> from dmr.settings import Settings
        >>> DMR_SETTINGS = {Settings.validate_responses: False}

    .. tab:: :octicon:`checklist` The right way

      The "right way" is not to disable the validation,
      but to specify the correct schema to be returned from an endpoint.

      .. literalinclude:: /examples/using_controller/right_way.py
        :caption: views.py
        :language: python
        :linenos:
        :emphasize-lines: 30-37
