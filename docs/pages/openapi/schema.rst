Semantic schema
===============

``django-modern-rest`` has a lot of special features around generating
internal schema for the :ref:`response validation <response_validation>`.
The same schema is later used to build :doc:`openapi` spec.

Our design goal is to validate the most semantic schema possible.


Semantic schema generation
--------------------------

First of all, what is a semantic schema?
We define it as a schema that knows all the semantics of the given API.

- What response schemas can it return?
- What content types?
- What status codes?
- Which cookies and headers can it set?

In many frameworks these details are not important.
However, in our experience – these details are very important
when dealing with any big project / integration.

How do we build this semantic schema?

1. We enforce request and response validation.
   No status codes that are not specified in the schema are allowed.
   No extra / missing headers, no extra / missing cookies.
   If something goes against the schema – it is rejected by the validation
2. We try to make the schema building process user-friendly.
   For example, when you add :doc:`auth <../auth/common>` to your endpoint,
   auth instance will inject its part of the schema into the main one.
   This way you will see ``401`` response in the schema
   for all the endpoints which use auth.
   We surely allow to redefine any of this behavior

.. note::

  We allow users to make their schemas as dumb as regular ones
  with just a single setting: :data:`~dmr.settings.Settings.semantic_schema`.
  It will disable **all** semantic schema generation. Including response specs,
  security requirements, security schemes.

  You would still have the very basic OpenAPI schema,
  it would be similar to ones that FastAPI and others provide.

  You can also have more controll over schema generation with:

  - :data:`~dmr.settings.Settings.semantic_responses`
  - :data:`~dmr.settings.Settings.exclude_semantic_responses`
  - :data:`~dmr.settings.Settings.semantic_auth`
  - :data:`~dmr.settings.Settings.exclude_semantic_auth`

.. tip::

  Turn it off together with :data:`dmr.settings.Settings.validate_responses`
  if you don't need any of this schema generation / validation stuff.

The core part of the schema generation
is :meth:`dmr.metadata.EndpointMetadata.collect_response_specs`
which collects all the responses' metadata in a single place.
Each :class:`~dmr.metadata.ResponseSpec` knows what it returns in great detail.

And :class:`~dmr.openapi.generators.SecuritySchemeGenerator`
for security requirements and security schemes generation.


Customizing schema generation
-----------------------------

Here's how our settings priority works:

- We check exact setting for the specific thing we try to generate, like
  ``semantic_responses`` and ``semantic_auth``
- If it is not set, we fallback to ``semantic_schema`` value

For example, if you disabled ``semantic_schema=False`` generation globally
and then enabled ``semantic_auth=True`` for a single controller,
it will generate semantic security schemes and security requirements
just for endpoints in this controller.

Semantic schema
~~~~~~~~~~~~~~~

To disable all semantic schema generation you can disable it on several levels:

.. tabs::

  .. tab:: disable per endpoint

    Pass ``semantic_schema`` parameter
    to :func:`~dmr.endpoint.modify` or :func:`~dmr.endpoint.validate`.

    .. literalinclude:: /examples/openapi/semantic_schema_per_endpoint.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: disable per controller

    Customize :attr:`~dmr.controller.Controller.semantic_schema` attribute.

    .. literalinclude:: /examples/openapi/semantic_schema_per_controller.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: disable per settings

    Exclude some semantic responses globally:

    .. code-block:: python
      :caption: settings.py
      :linenos:

      >>> from dmr.settings import Settings, DMR_SETTINGS

      >>> DMR_SETTINGS = {Settings.semantic_schema: False}

This will disable both semantic responses and semantic auth.

Semantic responses
~~~~~~~~~~~~~~~~~~

All endpoints by default generate semantic responses.
However, we allow several customizations.

You can disable some specific semantic responses generation by status code:

.. tabs::

  .. tab:: exclude per endpoint

    Pass ``exclude_semantic_responses`` parameter
    to :func:`~dmr.endpoint.modify` or :func:`~dmr.endpoint.validate`.

    .. literalinclude:: /examples/openapi/exclude_per_endpoint.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: exclude per controller

    Customize :attr:`~dmr.controller.Controller.exclude_semantic_responses`
    attribute.

    .. literalinclude:: /examples/openapi/exclude_per_controller.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: exclude per settings

    Exclude some semantic responses globally:

    .. code-block:: python
      :caption: settings.py
      :linenos:

      >>> from dmr.settings import Settings, DMR_SETTINGS

      >>> DMR_SETTINGS = {Settings.exclude_semantic_responses: {422}}

Or disable semantic responses completely:

.. tabs::

  .. tab:: per endpoint

    Pass ``semantic_responses`` parameter
    to :func:`~dmr.endpoint.modify` or :func:`~dmr.endpoint.validate`.

    .. literalinclude:: /examples/openapi/per_endpoint.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: per controller

    Customize :attr:`~dmr.controller.Controller.semantic_responses` attribute.

    .. literalinclude:: /examples/openapi/per_controller.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: per settings

    Disable semantic responses globally
    via :data:`~dmr.settings.Settings.semantic_responses` setting.

    .. code-block:: python
      :caption: settings.py
      :linenos:

      >>> from dmr.settings import Settings, DMR_SETTINGS

      >>> DMR_SETTINGS = {Settings.semantic_responses: False}

Semantic auth
~~~~~~~~~~~~~

All :class:`~dmr.security.SyncAuth` and :class:`~dmr.security.AsyncAuth`
instances by default generate semantic
security requirement and security schemes.
However, we allow several customizations.

You can disable some specific semantic security schemes
and security requirements generation by scheme name:

.. tabs::

  .. tab:: exclude per endpoint

    Pass ``exclude_semantic_auth`` parameter
    to :func:`~dmr.endpoint.modify` or :func:`~dmr.endpoint.validate`.

    .. literalinclude:: /examples/openapi/exclude_auth_per_endpoint.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: exclude per controller

    Customize :attr:`~dmr.controller.Controller.exclude_semantic_auth`
    attribute.

    .. literalinclude:: /examples/openapi/exclude_auth_per_controller.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: exclude per settings

    Exclude some semantic auth schemes and requirements globally:

    .. code-block:: python
      :caption: settings.py
      :linenos:

      >>> from dmr.settings import Settings, DMR_SETTINGS

      >>> DMR_SETTINGS = {Settings.exclude_semantic_auth: {'jwt'}}

Or disable semantic auth completely:

.. tabs::

  .. tab:: per endpoint

    Pass ``semantic_auth`` parameter
    to :func:`~dmr.endpoint.modify` or :func:`~dmr.endpoint.validate`.

    .. literalinclude:: /examples/openapi/semantic_auth_per_endpoint.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: per controller

    Customize :attr:`~dmr.controller.Controller.semantic_auth` attribute.

    .. literalinclude:: /examples/openapi/semantic_auth_per_controller.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: per settings

    Disable semantic auth globally
    via :data:`~dmr.settings.Settings.semantic_auth` setting.

    .. code-block:: python
      :caption: settings.py
      :linenos:

      >>> from dmr.settings import Settings, DMR_SETTINGS

      >>> DMR_SETTINGS = {Settings.semantic_auth: False}

.. note::

  When disabling semantic auth on controller / endpoint levels,
  security schemes can still be registered if some other endpoints need them.


.. _openapi-exclude-views:

Excluding views from OpenAPI
----------------------------

You can exclude individual endpoints, controllers, or entire routers
from OpenAPI. Excluded routes continue to work normally (including schema
validation), but are not visible in the generated specification.

We support three levels of configuration with this feature:

.. tabs::

  .. tab:: per endpoint

    Pass ``ignore_from_spec`` parameter
    to :func:`~dmr.endpoint.modify` or :func:`~dmr.endpoint.validate`
    on endpoints that you want to ignore.

    .. literalinclude:: /examples/openapi/ignore_endpoint.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: per controller

    Customize :attr:`~dmr.controller.Controller.ignore_from_spec` attribute.
    Endpoints can override this value with ``ignore_from_spec`` parameter.

    .. literalinclude:: /examples/openapi/ignore_controller.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: per router

    Pass ``ignore_from_spec`` parameter
    to :class:`~dmr.routing.Router` to exclude all routes from this router.

    When routers are nested, ``ignore_from_spec`` excludes the whole
    router subtree. Runtime URL routing is not affected.

    .. literalinclude:: /examples/openapi/ignore_router.py
      :caption: urls.py
      :linenos:
      :language: python
