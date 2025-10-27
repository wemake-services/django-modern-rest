Returning responses
===================

.. warning::

  Despite the fact, that ``django-modern-rest`` does not have
  its own requests and responses primitives
  and uses :class:`~django.http.HttpRequest`
  and :class:`~django.http.HttpResponse`,
  users must not return Django responses directly.

  Use instead any of the public APIs:

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

By default, all responses are validated at runtime to match the schema.
This allows us to be super strict about schema generation as a pro,
but as a con, it is slower than can possibly be.

You can disable response validation via configuration:
per endpoint, per controller, and globally.


.. _response_validation:

Response validation
-------------------
