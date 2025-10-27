Returning responses
===================

.. warning::

  Despite the fact, that ``django-modern-rest`` does not have
  its own request and response primitives
  and uses :class:`~django.http.HttpRequest`
  and :class:`~django.http.HttpResponse`,
  users must not return Django responses directly.

  Instead, use any of the public APIs:

  - :meth:`~django_modern_rest.controller.Controller.to_response`
  - :meth:`~django_modern_rest.controller.Controller.to_error`
  - :exc:`~django_modern_rest.response.APIError`

  In case when you don't have a controller / endpoint instance
  (like in a middleware, for example),
  you can fallback to using :func:`~django_modern_rest.response.build_response`
  lower level primitive.

  Why?

  1. You can mess up the default headers / status codes
  2. You won't have the right json serializer / deserializer,
     which can be both slow and error-prone


Describing response
-------------------


.. _response_validation:

Response validation
-------------------

By default, all responses are validated at runtime to match the schema.
This allows us to be super strict about schema generation as a pro,
but as a con, it is slower than can possibly be.

You can disable response validation via configuration:

.. warning::

  Disabling response validation makes sense only
  in production for better performance.

  It is not recommended to disable response validation for any other reason.
  Instead, fix your schema errors!

.. tabs::

    .. tab:: Active validation

      .. literalinclude:: /examples/returning_responses/active_validation.py
        :caption: views.py
        :linenos:
        :emphasize-lines: 26-27

    .. tab:: Disable per endpoint

      .. literalinclude:: /examples/returning_responses/per_endpoint.py
        :caption: views.py
        :linenos:
        :emphasize-lines: 6, 24

    .. tab:: Disable per controller

      .. literalinclude:: /examples/returning_responses/per_controller.py
        :caption: views.py
        :linenos:
        :emphasize-lines: 24-25

    .. tab:: Disable globally

      .. code-block:: python
        :caption: settings.py

        >>> DMR_SETTINGS = {'validate_responses': False}

    .. tab:: :octicon:`checklist` The right way

      .. literalinclude:: /examples/returning_responses/right_way.py
        :caption: views.py
        :linenos:
        :emphasize-lines: 11-12, 31-38
