OpenAPI
=======

We support OpenAPI versions from ``3.0.0`` through ``3.2.0``.

.. note::

  By default, we use OpenAPI ``3.1.0``, since tooling such as Swagger, Scalar,
  Redoc, and Stoplight does not yet fully support the latest specification.
  You can track the `current progress here <https://github.com/wemake-services/django-modern-rest/issues/519>`_.


Setting up OpenAPI views
------------------------

We support:

- `Swagger <https://github.com/swagger-api/swagger-ui>`_
  with :class:`~dmr.openapi.views.SwaggerView`
- `Redoc <https://github.com/Redocly/redoc>`_
  with :class:`~dmr.openapi.views.RedocView`
- `Scalar <https://github.com/scalar/scalar>`_
  with :class:`~dmr.openapi.views.ScalarView`
- `Stoplight Elements <https://github.com/stoplightio/elements>`_
  with :class:`~dmr.openapi.views.StoplightView`
- ``openapi.json`` with :class:`~dmr.openapi.views.OpenAPIJsonView`
- ``openapi.yaml`` with :class:`~dmr.openapi.views.yaml.OpenAPIYamlView`
  when ``[openapi]`` extra is installed

.. important::

  We recommend installing ``'django-modern-rest[openapi]'`` when working with
  OpenAPI. It enables schema validation, adds
  :class:`~dmr.openapi.views.yaml.OpenAPIYamlView`, and supports
  :ref:`automatic example generation <openapi-examples-generation>`.

Here's how it works:

.. literalinclude:: /examples/openapi/setting_up_schema.py
  :caption: urls.py
  :language: python
  :linenos:

And then visit https://localhost:8000/docs/swagger/ (or any other renderer)
for the interactive docs.

.. image:: /_static/images/swagger.png
   :alt: Swagger view
   :align: center

What happens in the example above?

1. We create / take an existing API :class:`dmr.routing.Router` instance
   and create an OpenAPI schema
   from it using :func:`~dmr.openapi.build_schema`
2. Next, we define regular Django views that will serve you the API renderers
3. You can modify these views
   to :func:`require auth / role / permissions / etc <django.contrib.auth.decorators.login_required>`
   as all other regular Django views

Requirements for OpenAPI UIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The HTML OpenAPI renderers
(:class:`~dmr.openapi.views.SwaggerView`,
:class:`~dmr.openapi.views.RedocView`,
:class:`~dmr.openapi.views.ScalarView`, and
:class:`~dmr.openapi.views.StoplightView`)
depend on both Django templates and static files.

To use the bundled UI pages:

- Add ``'dmr'`` to ``INSTALLED_APPS``, so Django can discover the bundled
  renderer templates
- If you serve bundled assets locally, add
  ``'django.contrib.staticfiles'`` to ``INSTALLED_APPS``
- Configure Django templates so app templates can be discovered, for example
  by enabling
  `APP_DIRS <https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-TEMPLATES-APP_DIRS>`_
  in the Django template backend
- Set
  `STATIC_URL <https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-STATIC_URL>`_
  so Django can generate URLs for bundled static assets

In development, this is usually enough when using Django's development server.

In production, make sure your static files setup is correct as described in the
`Django static files documentation <https://docs.djangoproject.com/en/stable/howto/static-files/>`_
and the
`staticfiles app reference <https://docs.djangoproject.com/en/stable/ref/contrib/staticfiles/>`_.

If you switch renderers to CDN assets via
:data:`dmr.settings.Settings.openapi_static_cdn`,
local static file serving is no longer required for those assets,
but adding ``'dmr'`` to the list of installed apps and template
discovery are **still required**.

.. note::

  By default, Swagger, Redoc, Stoplight, and Scalar use bundled static assets
  shipped with ``django-modern-rest`` and served by Django.
  To switch any renderer to a CDN, configure
  :data:`dmr.settings.Settings.openapi_static_cdn`.
  Only renderers listed in that mapping will use CDN;
  all others keep using local static files.
  Exact bundled versions and license texts are documented in ``licenses/``.

  You can also modify the exact versions that we use for each tool this way.

  Example:

  .. code-block:: python
    :caption: settings.py

    >>> from dmr.settings import Settings

    >>> DMR_SETTINGS = {
    ...     Settings.openapi_static_cdn: {
    ...         # or `@5.32.1`, or whatever other version:
    ...         'swagger': 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.32.0',
    ...     },
    ... }


Choosing a renderer and CSP
---------------------------

For the general ``Content-Security-Policy`` setup with Django, see
:ref:`content_security_policy`.

For OpenAPI specifically, the main thing to keep in mind is that final CSP
compatibility still depends on the upstream renderer bundle you choose.

In general:

- :class:`~dmr.openapi.views.SwaggerView` is usually the best default when
  you want interactive docs with "try it out" support.
- :class:`~dmr.openapi.views.RedocView` is a good fit for mostly read-only,
  reference-style documentation.
- :class:`~dmr.openapi.views.ScalarView` and
  :class:`~dmr.openapi.views.StoplightView` are worth considering when you
  prefer their UI, but they tend to be more opinionated frontends with more
  moving parts.

Known caveats:

- If you switch to CDN assets, your CSP must allow those remote origins too.
- In practice, Swagger and Redoc are usually easier starting points than more
  feature-heavy frontend bundles.


Customizing OpenAPI config
--------------------------

We support customizing :class:`dmr.openapi.OpenAPIConfig`
that will be used for the final schema in two ways:

1. By defining :data:`dmr.settings.Settings.openapi_config` setting
   inside ``DMR_SETTINGS`` in your ``settings.py``
2. By passing ``OpenAPIConfig`` instance
   into :func:`~dmr.openapi.build_schema`

For example, this is how you can change some OpenAPI metadata,
including the spec version:

.. literalinclude:: /examples/openapi/custom_config.py
  :caption: urls.py
  :language: python
  :linenos:


Customizing OpenAPI generation
------------------------------

Customizing schema
~~~~~~~~~~~~~~~~~~

We delegate all schema generation to the model's library directly.
To do so, we use :class:`~dmr.serializer.BaseSchemaGenerator`
subclasses for different serializers.

To customize a schema, use the native methods.

.. tabs::

  .. tab:: msgspec

    Docs: https://jcristharif.com/msgspec/jsonschema.html

    .. literalinclude:: /examples/openapi/msgspec_customization.py
      :caption: dtos.py
      :language: python
      :linenos:
      :no-imports-spoiler:

  .. tab:: pydantic

    Docs: https://docs.pydantic.dev/latest/concepts/json_schema

    .. literalinclude:: /examples/openapi/pydantic_customization.py
      :caption: dtos.py
      :language: python
      :linenos:
      :no-imports-spoiler:

    Common features:

    - You can completely redefine the schema generation with providing
      :class:`pydantic.json_schema.WithJsonSchema` annotation
      or by overriding ``__get_pydantic_json_schema__`` method
      on a pydantic model
    - You can change the ``title`` of generics pydantic models
      by redefining :meth:`pydantic.BaseModel.model_parametrized_name`

.. note::

  By default docstring or ``__doc__`` from the model is used as a description.

Customizing path items
~~~~~~~~~~~~~~~~~~~~~~

:class:`~dmr.controller.Controller` allows customizing some metadata
for :class:`~dmr.openapi.objects.PathItem`:

.. literalinclude:: /examples/openapi/path_item_customization.py
  :caption: views.py
  :language: python
  :linenos:

.. note::

  By default docstring or ``__doc__`` from the controller
  is used to generate summary and description
  for the :class:`~dmr.openapi.objects.PathItem`.

Customizing operation
~~~~~~~~~~~~~~~~~~~~~

:deco:`~dmr.endpoint.modify` and :deco:`~dmr.endpoint.validate`
can be used to customize the resulting :class:`~dmr.openapi.objects.Operation`
metadata.

.. literalinclude:: /examples/openapi/operation_customization.py
  :caption: views.py
  :language: python
  :linenos:

.. note::

  By default docstring or ``__doc__`` from endpoint's function definition
  is used to generate summary and description
  for the :class:`~dmr.openapi.objects.Operation`.

Customizing router-level metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~dmr.routing.Router` supports ``tags`` and ``deprecated`` parameters
to apply OpenAPI metadata to all operations in the router:

.. literalinclude:: /examples/openapi/router_metadata.py
  :caption: urls.py
  :language: python
  :linenos:

- ``tags``: List of strings to group operations in OpenAPI documentation
- ``deprecated``: Boolean flag to mark all operations in this router as deprecated

These router-level settings are automatically merged with endpoint-level customizations
set via :deco:`~dmr.endpoint.modify` or :deco:`~dmr.endpoint.validate`.
Router tags are prepended to endpoint tags, and deprecated is set to ``True``
if either the router or endpoint has it enabled.

You can also set ``tags`` and ``deprecated`` at the individual endpoint level
via :deco:`~dmr.endpoint.modify` to override or extend router-level settings.


.. _customizing_parameter_openapi:

Customizing parameter
~~~~~~~~~~~~~~~~~~~~~

There are different styles and other features
that :class:`~dmr.openapi.objects.Parameter` supports
in `OpenAPI Parameters <https://learn.openapis.org/specification/parameters.html>`_.

For example, if you want to change how :data:`~dmr.components.Query`
parameter is documented with the help
of :class:`dmr.openapi.objects.ParameterMetadata` annotation:

.. literalinclude:: /examples/openapi/parameter_customization.py
  :caption: views.py
  :language: python
  :linenos:


.. _customizing_body_openapi:

Customizing media types
~~~~~~~~~~~~~~~~~~~~~~~

There are different metadata fields, like ``examples`` and ``encoding``,
that :class:`~dmr.openapi.objects.MediaType` supports
in `OpenAPI MediaType <https://spec.openapis.org/oas/latest#media-type-object>`_.

For example, if you want to change how :data:`~dmr.components.Body`
provides examples,
you can use :class:`dmr.openapi.objects.MediaTypeMetadata` annotation:

.. literalinclude:: /examples/openapi/request_body_customization.py
  :caption: views.py
  :language: python
  :linenos:

We also support the same way for conditional types:

.. literalinclude:: /examples/openapi/request_conditional_body_customization.py
  :caption: views.py
  :language: python
  :linenos:

And for :data:`~dmr.components.FileMetadata`:

.. literalinclude:: /examples/openapi/request_files_customization.py
  :caption: views.py
  :language: python
  :linenos:

Customizing response
~~~~~~~~~~~~~~~~~~~~

:class:`~dmr.metadata.ResponseSpec` supports all the metadata fields
that :class:`~dmr.openapi.objects.Response` has.

Providing an explicit :class:`~dmr.openapi.objects.Link` for ``schemathesis``
`stateful API testing <https://schemathesis.readthedocs.io/en/stable/explanations/stateful>`_
would look like so:

.. literalinclude:: /examples/openapi/response_customization.py
  :caption: views.py
  :language: python
  :linenos:


.. _openapi-examples-generation:

Examples generation
-------------------

If you installed ``'django-modern-rest[openapi]'`` extra
and enabled :data:`~dmr.settings.Settings.openapi_examples_seed` setting,
we will generate missing examples in your OpenAPI schemas using
`polyfactory <https://github.com/litestar-org/polyfactory>`_.

They will not have the best data quality, since
they are clearly autogenerated from fake data,
but sometimes it is better than nothing.

.. literalinclude:: /examples/openapi/example_generation.py
  :caption: views.py
  :language: python
  :linenos:

.. important::

  However, we recommend adding semantic named examples by hand.


Top level API
-------------

This is how OpenAPI spec is generated, top level overview:

.. mermaid::
  :caption: OpenAPI spec generation
  :config: {"theme": "forest"}

  graph
      Start[build_schema] --> Router[Router];
      Router -->|for each controller| Controller[Controller.get_path_item];
      Router -->|for each defined auth| SecurityScheme[Auth.security_scheme];
      Controller -->|for each endpoint| Endpoint[Endpoint.get_schema];
      Endpoint -->|for each component| ComponentParser[ComponentParser.get_schema]
      Endpoint -->|for each response| ResponseSpec[ResponseSpec.get_schema];
      Endpoint -->|for each used auth| SecurityRequirement[Auth.security_requirement];
      ComponentParser -->|for each schema| Schema[serializer.schema_generator.get_schema];
      ResponseSpec -->|for each schema| Schema[serializer.schema_generator.get_schema];

We have several major design principles that define our API:

1. Regular user-facing objects must know how to build the OpenAPI schema.
   For example: :class:`~dmr.endpoint.Endpoint`,
   :class:`~dmr.controller.Controller`, and :class:`~dmr.routing.Router`
   all know how to build the spec for themselves.
   Since they are user-facing, it is easy to modify
   how the schema generation works if needed
2. All model schemas must be directly generated by their libraries.
   We don't do anything with the JSON Schema that is generated
   by ``pydantic`` or ``msgspec``. They can do a better job than we do.
   However, their schemas still can be customized.
   See :class:`~dmr.plugins.pydantic.schema.PydanticSchemaGenerator`
   and :class:`~dmr.plugins.msgspec.schema.MsgspecSchemaGenerator`

APIs for schema overrides
~~~~~~~~~~~~~~~~~~~~~~~~~

Useful APIs for users to override:

- :func:`dmr.openapi.build_schema` to change
  how :class:`~dmr.openapi.OpenAPIConfig`
  and :class:`~dmr.openapi.OpenAPIContext` are generated
- :meth:`dmr.routing.Router.get_schema` to change
  how :class:`~dmr.openapi.objects.OpenAPI`
  and :class:`~dmr.openapi.objects.Components` are generated
- :meth:`dmr.controller.Controller.get_path_item` to change how
  :class:`~dmr.openapi.objects.PathItem` objects are generated
- :meth:`dmr.endpoint.Endpoint.get_schema` to change how
  :class:`~dmr.openapi.objects.Operation` is generated
- :meth:`dmr.components.ComponentParser.get_schema` to change how
  :class:`~dmr.openapi.objects.Parameter` objects are generated
- :meth:`dmr.metadata.ResponseSpec.get_schema` to change how
  :class:`~dmr.openapi.objects.Response` objects are generated
- :meth:`dmr.security.SyncAuth.security_schemes`
  and :class:`dmr.security.SyncAuth.security_requirement` to change how
  :class:`~dmr.openapi.objects.SecurityScheme` and requirements are generated


API Reference
-------------

This is the API every user needs:

.. autofunction:: dmr.openapi.build_schema

.. autoclass:: dmr.openapi.OpenAPIConfig
   :members:

.. autoclass:: dmr.openapi.OpenAPIContext
  :members:

All other objects that are only used if you decide to customize the schema
are listed in :doc:`openapi-reference`.
