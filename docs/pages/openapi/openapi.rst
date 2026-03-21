OpenAPI
=======

We support OpenAPI versions from ``3.0`` all the way up including ``3.2``.

Default OpenAPI version is ``3.1``, because as of right now (12-03-2026)
Swagger / Scalar / Redoc do not fully support ``3.2`` yet.
See `the progress here <https://github.com/wemake-services/django-modern-rest/issues/519>`_.

Setting up OpenAPI views
------------------------

We support:

- `Swagger <https://github.com/swagger-api/swagger-ui>`_
  with :class:`~dmr.openapi.views.SwaggerView`
- `Redoc <https://github.com/Redocly/redoc>`_
  with :class:`~dmr.openapi.views.RedocView`
- `Scalar <https://github.com/scalar/scalar>`_
  with :class:`~dmr.openapi.views.ScalarView`
- ``openapi.json`` with :class:`~dmr.openapi.views.OpenAPIJsonView`

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

.. important::

  Make sure that ``'dmr'`` is listed in the ``INSTALLED_APPS``
  and that static files are enabled,
  so we can serve you the required static files.

.. note::

  By default Swagger, Redoc, and Scalar use bundled static assets
  that are shipped with ``django-modern-rest`` and served by Django.
  To switch any renderer to a CDN, configure
  :data:`dmr.settings.Settings.openapi_static_cdn`.
  Only renderers listed in that mapping will use CDN;
  all others keep using local static files.
  Exact bundled versions and license texts are documented in ``licenses/``.


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

      You can completely redefine the schema generation with
      overriding ``__get_pydantic_json_schema__`` method on a pydantic model.

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


.. _customizing_parameter_openapi:

Customizing parameter
~~~~~~~~~~~~~~~~~~~~~

There are different styles and other features
that :class:`~dmr.openapi.objects.Parameter` supports
in `OpenAPI Parameters <https://learn.openapis.org/specification/parameters.html>`_.

For example, if you want to change how :class:`~dmr.components.Query`
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

For example, if you want to change how :class:`~dmr.components.Body`
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

And for :class:`~dmr.components.FileMetadata`:

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
  :caption: Error handling logic
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
