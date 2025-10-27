Configuration
=============

.. module:: django_modern_rest.settings

We use ``DMR_SETTINGS`` dictionary object to store all the configuration.

.. note::

  Remember, that ``django_modern_rest`` settings
  are cached after the first access.
  If you need to modify settings dynamically
  in runtime use :func:`~django_modern_rest.settings.clear_settings_cache`.

Here are all keys and values that can be set.
To configure ``django-modern-rest`` place this into your ``settings.py``:


JSON Parsing
------------

.. note::

  It is recommended to always install ``msgspec``
  with ``'django-modern-rest[msgspec]'`` extra for better performance.

.. data:: serialize

  Default: ``'django_modern_rest.internal.json.serialize'``

  String or callable object that will serialize and objects to json for you.

  By default uses ``json`` module for serialization
  if ``msgspec`` is not installed.
  And uses ``msgspec.json`` if ``msgspec`` is installed.

  Custom configuration example, let's say you want to always use ``ujson``:

  .. code-block:: python
    :caption: settings.py

    >>> DMR_SETTINGS = {'serialize': 'path.to.your.ujson.serialize'}

  See :class:`~django_modern_rest.internal.json.Serialize` for the callback type.


.. data:: deserialize

  Default: ``'django_modern_rest.internal.json.deserialize'``

  String or callable object that will deserialize and objects from json for you.

  By default uses ``json`` module for deserialization
  if ``msgspec`` is not installed.
  And uses ``msgspec.json`` if ``msgspec`` is installed.

  Custom configuration example, let's say you want to always use ``ujson``:

  .. code-block:: python
    :caption: settings.py

    >>> DMR_SETTINGS = {'deserialize': 'path.to.your.ujson.deserialize'}

  See :class:`~django_modern_rest.internal.json.Deserialize`
  for the callback type.


Response handling
-----------------

.. data:: responses

  Default: ``[]``

  The list of global :class:`~django_modern_rest.response.ResponseDescription`
  object that will be added to all endpoints' metadata
  as a possible response schema.

  Use it to set global responses' status codes like ``500``:

  .. code-block:: python
    :caption: settings.py

    >>> from http import HTTPStatus
    >>> from typing_extensions import TypedDict
    >>> from django_modern_rest.response import ResponseDescription

    >>> class Error(TypedDict):
    ...     detail: str

    >>> # If our API can always return a 500 response with `{"detail": str}`
    >>> # error message:
    >>> DMR_SETTINGS = {
    ...     'responses': [
    ...         ResponseDescription(
    ...             Error,
    ...             status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
    ...         ),
    ...     ],
    ... }

.. data:: validate_responses

  Default: ``True``

  When some endpoint returns any data, we by default validate
  that this data matches the endpoint schema.

  So, this code will produce not only static typing error,
  but also a runtime error:

  .. code:: python

    >>> from django_modern_rest import Controller
    >>> from django_modern_rest.plugins.pydantic import PydanticSerializer

    >>> class MyController(Controller[PydanticSerializer]):
    ...     def get(self) -> list[str]:
    ...         return [1, 2]  # <- both static typing and runtime error

  But, there's a runtime cost to this. It is recommended to switch
  this validation off for production:

  .. code-block:: python
    :caption: settings.py

    >>> DMR_SETTINGS = {'validate_responses': False}

  .. note::

    You can also switch off this validation per-controller
    with :attr:`~django_modern_rest.controller.Controller.validate_responses`
    and per-endpoint with ``validate_responses`` argument
    to :func:`~django_modern_rest.endpoint.modify`
    and :func:`~django_modern_rest.endpoint.validate`.


Error handling
--------------

.. data:: global_error_handler

  Default: ``'django_modern_rest.errors.global_error_handler'``

  String or a function to globally handle all errors in the application.
  Here's our error handling hieracy:

  1. Per-endpoint with
     :meth:`~django_modern_rest.endpoint.Endpoint.handle_error`
     and :meth:`~django_modern_rest.endpoint.Endpoint.handle_async_error`
  2. Per-controller with
     :meth:`~django_modern_rest.controller.Controller.handle_error`
     or :meth:`~django_modern_rest.controller.Controller.handle_async_error`
  3. If nothing helped, ``'global_error_handler'`` is called

  See :func:`~django_modern_rest.errors.global_error_handler`
  for the callback type.

  .. code-block:: python
    :caption: settings.py

    >>> DMR_SETTINGS = {'global_error_handler': 'path.to.your.handler'}


.. autofunction:: django_modern_rest.errors.global_error_handler


Environment variables
---------------------

.. envvar:: DMR_MAX_CACHE_SIZE

  Default: ``256``

  We use :func:`functools.lru_cache` in many places internally.
  For example:

  - To create json encoders and decoders only once
  - To create type validation objects
    in :class:`~django_modern_rest.serialization.BaseEndpointOptimizer`

  You can control the size / memory usage with this setting.

  Increase if you have a lot of different return types.


Misc
----

.. autofunction:: django_modern_rest.settings.clear_settings_cache
