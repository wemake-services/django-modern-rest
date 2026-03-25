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
  with just a single setting: :data:`~dmr.settings.Settings.semantic_responses`.

  Turn it off together with :data:`dmr.settings.Settings.validate_responses`
  if you don't need any of this schema stuff.
  You would still have the very basic OpenAPI schema,
  it would be similar to ones that FastAPI and others provide.

The core part of the schema generation
is :meth:`dmr.metadata.EndpointMetadata.collect_response_specs`
which collects all the responses' metadata in a single place.

Each :class:`~dmr.metadata.ResponseSpec` knows what it returns in great detail.


Customizing schema generation
-----------------------------

All endpoints by default generate semantic responses.
However, we allow 4 levels of customizations.

First non ``None`` value wins:

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

      Disable semantic responses globally:

      .. code-block:: python
        :caption: settings.py
        :linenos:

        >>> from dmr.settings import Settings, DMR_SETTINGS

        >>> DMR_SETTINGS = {Settings.semantic_responses: False}
