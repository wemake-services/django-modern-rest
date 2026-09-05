.. _response_validation:

Response validation
===================

By default, all responses (not just requests!)
are validated at runtime to match the schema.
This allows us to be super strict about schema generation as a pro,
but as a con, it is slower than it could possibly be.

So, you can disable response validation via configuration:

.. warning::

  Disabling response validation makes sense only
  in production for better performance.

  It is not recommended to disable response validation for any other reason.
  Instead, fix your schema errors!

  Keep it on in development, but disable
  it in production to get the best of both worlds.

.. tabs::

  .. tab:: Active validation

    .. literalinclude:: /examples/using_controller/active_validation.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: Disable per endpoint

    .. literalinclude:: /examples/using_controller/per_endpoint.py
      :caption: views.py
      :language: python
      :linenos:
      :emphasize-lines: 19

  .. tab:: Disable per controller

    .. literalinclude:: /examples/using_controller/per_controller.py
      :caption: views.py
      :language: python
      :linenos:
      :emphasize-lines: 20

  .. tab:: Disable globally

    See :data:`dmr.settings.Settings.validate_responses`.

    .. code-block:: python
      :caption: settings.py

      >>> from dmr.settings import Settings
      >>> DMR_SETTINGS = {Settings.validate_responses: False}


.. _exclude-validate-responses-levels:

Excluding some status codes
---------------------------

.. versionadded:: 0.15.0

Sometimes you don't want to disable the validation completely,
you just have status codes that are not in your schema.
``500`` is the usual one.

List them in :data:`~dmr.settings.Settings.exclude_validate_responses`
to let such responses through:

.. code-block:: python
  :caption: settings.py

  >>> from http import HTTPStatus
  >>> from dmr.settings import Settings

  >>> DMR_SETTINGS = {
  ...     Settings.exclude_validate_responses: {
  ...         HTTPStatus.INTERNAL_SERVER_ERROR,
  ...     },
  ... }

The same works per-controller with
:attr:`~dmr.controller.Controller.exclude_validate_responses`
and per-endpoint with the argument of the same name
to :func:`~dmr.endpoint.modify` and :func:`~dmr.endpoint.validate`.
Setting it to ``None`` on any level resets all the other levels.

All other status codes are still validated as usual.
See :ref:`error-responses-validation` for when this is the right call
and what the alternatives are.


The right way
-------------

The "right way" is not to disable the validation,
but to specify the correct schema to be returned from an endpoint.

.. literalinclude:: /examples/using_controller/right_way.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 20-25


And to disable the validation for ``production`` environment.
Example: https://github.com/wemake-services/wemake-django-template/blob/c003757fd33ba7dd1a9e7af7c3a175883d0c033b/%7B%7Bcookiecutter.project_name%7D%7D/server/settings/environments/production.py#L86
