Configuration
=============

We use ``DMR_SETTINGS`` dictionary object to store all the configuration.
All keys are typed with :class:`~dmr.settings.Settings` enum keys
which can be used to both set and get settings.

.. note::

  Remember, that ``django-modern-rest`` settings
  are cached after the first access.
  If you need to modify settings dynamically
  in runtime use :func:`~dmr.settings.clear_settings_cache`.
  You can modify the size of cache with adjusting
  :envvar:`DMR_MAX_CACHE_SIZE` value.

Here are all keys and values that can be set.
As usual, all settings go to ``settings.py`` file in your Django project.

.. seealso::

  - Official Django settings docs:
    https://docs.djangoproject.com/en/5.2/topics/settings
  - ``django-split-settings`` configuration helper
    https://github.com/wemake-services/django-split-settings


.. autoclass:: dmr.settings.Settings
  :show-inheritance:

  To get settings use
  :func:`~dmr.settings.resolve_setting` function
  together with ``Settings`` keys:

  .. code:: python

    >>> from dmr.settings import Settings, resolve_setting

    >>> resolve_setting(Settings.responses)
    []

  To set settings use:

  .. code:: python

    >>> DMR_SETTINGS = {Settings.responses: []}


Content negotiation
-------------------

.. note::

  It is recommended to always install ``msgspec``
  with ``'django-modern-rest[msgspec]'`` extra for better performance.

.. data:: dmr.settings.Settings.parsers

  Default: :class:`dmr.parsers.JsonParser` or
  :class:`dmr.plugins.msgspec.MsgspecJsonParser` if installed.

  A list of instances of subtypes
  of :class:`~dmr.parsers.Parser`
  to serialize data from the requested text format,
  like json or xml, into python object.

  By default uses ``json`` module for deserialization
  if ``msgspec`` is not installed.
  And uses ``msgspec.json`` if ``msgspec`` is installed.

  Custom configuration example, let's say you want to always use ``ujson``:

  .. code-block:: python
    :caption: settings.py

    >>> from dmr.parsers import JsonParser
    >>> DMR_SETTINGS = {Settings.parsers: [JsonParser()]}

.. data:: dmr.settings.Settings.renderers

  Default: :class:`dmr.renderers.JsonRenderer` or
  :class:`dmr.plugins.msgspec.MsgspecJsonRenderer` if installed.

  A list of instances of subtypes
  of :class:`~dmr.renderers.Renderer`
  to serialize python objects to the requested text format, like json or xml.

  By default uses ``json`` module for serialization
  if ``msgspec`` is not installed.
  And uses ``msgspec.json`` if ``msgspec`` is installed which are faster.

  Custom configuration example, let's say you want to always use ``ujson``:

  .. code-block:: python
    :caption: settings.py

    >>> from dmr.renderers import JsonRenderer
    >>> DMR_SETTINGS = {Settings.renderers: [JsonRenderer()]}


Response handling
-----------------

.. data:: dmr.settings.Settings.responses

  Default: ``[]``

  The list of global :class:`~dmr.metadata.ResponseSpec`
  object that will be added to all endpoints' metadata
  as a possible response schema.

  Use it to set global responses' status codes like ``500``:

  .. code-block:: python
    :caption: settings.py

    >>> from http import HTTPStatus
    >>> from typing_extensions import TypedDict
    >>> from dmr import ResponseSpec

    >>> class Error(TypedDict):
    ...     detail: str

    >>> # If our API can always return a 500 response with `{"detail": str}`
    >>> # error message:
    >>> DMR_SETTINGS = {
    ...     Settings.responses: [
    ...         ResponseSpec(
    ...             Error,
    ...             status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
    ...         ),
    ...     ],
    ... }

.. data:: dmr.settings.Settings.validate_responses

  Default: ``True``

  When some endpoint returns any data, we by default validate
  that this data matches the endpoint schema.

  So, this code will produce not only static typing error,
  but also a runtime error:

  .. code:: python

    >>> from dmr import Controller
    >>> from dmr.plugins.pydantic import PydanticSerializer

    >>> class MyController(Controller[PydanticSerializer]):
    ...     def get(self) -> list[str]:
    ...         return [1, 2]  # <- both static typing and runtime error

  But, there's a runtime cost to this. It is recommended to switch
  this validation off for production:

  .. code-block:: python
    :caption: settings.py

    >>> DMR_SETTINGS = {Settings.validate_responses: False}

  .. note::

    You can also switch off this validation per-controller
    with :attr:`~dmr.controller.Blueprint.validate_responses`
    and per-endpoint with ``validate_responses`` argument
    to :func:`~dmr.endpoint.modify`
    and :func:`~dmr.endpoint.validate`.


Error handling
--------------

.. data:: dmr.settings.Settings.global_error_handler

  Default: ``'dmr.errors.global_error_handler'``

  Globally handle all errors in the application.
  You can use real object or string path for the object to be imported.
  Here's our error handling hieracy:

  1. Per-endpoint with
     :meth:`~dmr.endpoint.Endpoint.handle_error`
     and :meth:`~dmr.endpoint.Endpoint.handle_async_error`
  2. Per-controller with
     :meth:`~dmr.controller.Controller.handle_error`
     or :meth:`~dmr.controller.Controller.handle_async_error`
  3. If nothing helped, ``'global_error_handler'`` is called

  See :func:`~dmr.errors.global_error_handler`
  for the callback type.

  .. code-block:: python
    :caption: settings.py

    >>> DMR_SETTINGS = {Settings.global_error_handler: 'path.to.your.handler'}


Authentication
--------------

.. data:: dmr.settings.Settings.auth

  Default: ``[]``

  Configure authentication rules for the whole API.

  To enable auth for all endpoints you can use:

  .. code-block:: python
    :caption: settings.py

    >>> from dmr.security.django_session import DjangoSessionSyncAuth

    >>> DMR_SETTINGS = {
    ...     Settings.auth: [
    ...         DjangoSessionSyncAuth(),
    ...     ],
    ... }

  All auth types must be importable in settings.

  .. note::

    All auth classes must support initialization without parameters.


HTTP Spec validation
--------------------

.. data:: dmr.settings.Settings.no_validate_http_spec

  Default: ``frozenset()``

  A set of unique :class:`~dmr.settings.HttpSpec` codes
  to be globally disabled.

  We don't recommend disabling any of these checks globally.

  .. code-block:: python
    :caption: settings.py

    >>> from dmr.settings import HttpSpec

    >>> DMR_SETTINGS = {
    ...     Settings.no_validate_http_spec: {
    ...         HttpSpec.empty_request_body,
    ...     },
    ... }


.. autoclass:: dmr.settings.HttpSpec
  :show-inheritance:
  :members:


Hacks
-----

.. data:: dmr.settings.Settings.django_treat_as_post

  Default: ``frozenset({'PUT', 'PATCH'})``

  By default Django only populates
  :attr:`django.http.HttpRequest.POST`
  and :attr:`django.http.HttpRequest.FILES`
  for ``POST`` requests.

  Some parsers like :class:`~dmr.parsers.MultiPartParser`
  require ``.POST`` and ``.FILES`` to be set to work with
  :class:`~dmr.components.Body`
  and :class:`~dmr.components.FileMetadata`.

  However, we build REST APIs where more methods are in use, not just ``POST``.
  So, we use this setting to populate ``.POST`` and ``.FILES``
  when parser is a subtype of either
  :class:`~dmr.parsers.SupportsFileParsing`
  or :class:`~dmr.parsers.SupportsDjangoDefaultParsing`
  and we work with components that require request body.

  .. note::

    This is a really advanced setting. If you are not creating
    your own components or your own parsers - do not change it.


Environment variables
---------------------

.. envvar:: DMR_MAX_CACHE_SIZE

  Default: ``256``

  We use :func:`functools.lru_cache` in many places internally.
  For example:

  - To create json encoders and decoders only once
  - To create type validation objects
    in :class:`~dmr.serializer.BaseEndpointOptimizer`

  You can control the size / memory usage with this setting.

  Increase if you have a lot of different return types.


API Reference
-------------

.. autofunction:: dmr.settings.resolve_setting

.. autofunction:: dmr.settings.clear_settings_cache
