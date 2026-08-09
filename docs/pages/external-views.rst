External views
==============

``django-modern-rest`` is build around several pure-Django concepts:

- :class:`~dmr.controller.Controller` which is a subclass
  of :class:`~django.views.generic.base.View` to define API views
- :class:`~dmr.routing.Router` to manipulate ``URLPattern`` objects and URLs
- :class:`~dmr.openapi.openapi.OpenAPI` dataclass
  to store OpenAPI spec near the view

So, *any* Django-compatible :class:`~django.views.generic.base.View`
objects can be used with ``django-modern-rest``
with the user-provided OpenAPI schema.

.. important::

  ``'django-modern-rest[pydantic]'`` must be installed
  to use external views feature.
  :func:`~dmr.openapi.load_schema` requires it to deserialize OpenAPI objects.


How it works?
-------------

Just like good old Django!

We **don't touch the existing view logic / OpenAPI metadata in any way**.

The view itself can do any validation or logic,
parse / serialize objects in any way.
We also just include the existing OpenAPI metadata,
without any logic or modifications.

.. note::

  However, if you define top-level error handlers with
  :func:`~dmr.routing.build_404_handler`
  and :func:`~dmr.routing.build_500_handler`,
  it would still affect the view, when these error happen.

OpenAPI
~~~~~~~

Imagine that you already have an OpenAPI spec,
it might be from another library, old project, legacy service, etc.

But, we can continue to use it.
Let's say you have an existing service that returns you random numbers.
Here's its spec:

.. literalinclude:: /examples/external_views/openapi.yml
  :caption: openapi.yml
  :language: yaml
  :linenos:

Next, let's show how we can adapt existing
pure-Django API views, attach this existing schemaas:

- both functional,
- and class-based.

.. tip::

  If external OpenAPI has validation issues,
  you might want to disable the OpenAPI validation process for the whole schema.
  Pass ``skip_validation=False`` to the converter methods.
  See :meth:`dmr.openapi.openapi.OpenAPI.convert`
  and :meth:`dmr.openapi.views.base.OpenAPIView.as_view`.

Functional example
~~~~~~~~~~~~~~~~~~

Let's start with functions.
Our previously described random number API service can be a function:

.. literalinclude:: /examples/external_views/functions.py
  :caption: views.py
  :language: python
  :linenos:

Notice that ``/api/numbers`` path item definition from ``openapi.yml``
was inserted into our final schema as-is.

Class example
~~~~~~~~~~~~~

Now, the same, but with a class:

.. literalinclude:: /examples/external_views/classes.py
  :caption: views.py
  :language: python
  :linenos:

It can be any :class:`~django.views.generic.base.View` compatible class!


Registering OpenAPI schemas
---------------------------

Now, we have a new OpenAPI file. It has several changes from the first one:

- It contains :class:`int` path parameters ``start`` and ``end``
- It has a schema component with a ``$ref`` as a return,
  so we would have to register in the final spec
- It has top-level tags definition that we also want to copy to the final spec

It does the same thing,
but has two path parameters and also defines OpenAPI schemas
that we need to re-register, so they would be available in our final spec:

.. literalinclude:: /examples/external_views/openapi2.yml
  :caption: openapi.yml
  :language: yaml
  :linenos:

To register OpenAPI schema components and tags, we can use
:class:`dmr.openapi.OpenAPIConfig` customization:

.. literalinclude:: /examples/external_views/components.py
  :caption: views.py
  :language: python
  :linenos:

There are several rules on how we merge the pre-defined config
with the automatically generated one:

- When trying to redefine an existing component by name,
  :exc:`ValueError` is raised
- We merge all components from all possible types
- We can't detect unused ones, so we merge all,
  even if some of them are not used

If you have several :class:`~dmr.openapi.objects.Components` definitions,
you can pass a list of them to the :class:`dmr.openapi.OpenAPIConfig` instance.
All of them will be merged into the final spec correctly.

See :doc:`openapi/openapi` for more possible customizations.


Excluding external views from OpenAPI
-------------------------------------

It might be important to add a private API endpoint,
without registering it in the final OpenAPI spec.

Some endpoints might not even have OpenAPI in the first place!

To achieve this, pass ``None`` instead of the ``PathItem`` schema:

.. literalinclude:: /examples/external_views/ignore_from_spec.py
  :caption: views.py
  :language: python
  :linenos:

The view will still work as expected, but won't be present in the spec.

See :ref:`openapi-exclude-views` for more details
about excluding regular views from the OpenAPI.


Real world use-cases
--------------------

For example, one can reuse:

- ``django-allauth``
  `headles views <https://github.com/pennersr/django-allauth/tree/main/allauth/headless>`_
  that are built to be used by the pure Django framework
- Any ``APIView`` or ``GenericAPIView`` objects from ``django-rest-framework``
- Any ``ControllerBase`` objects from ``django-ninja-extra``
- And many more!
