External views
==============

``django-modern-rest`` is build around several pure-Django concepts:

- :class:`~dmr.controller.Controller` to define API views
- :class:`~dmr.routing.Router` to manipulate ``URLPattern`` objects and URLs
- :class:`~dmr.openapi.core.context.OpenAPIContext` to store
  the OpenAPI metadata

So, *any* Django-compatible :class:`~django.views.generic.base.View`
objects can be used with ``django-modern-rest``
with the user-provided OpenAPI schema.

.. important::

  ``'django-modern-rest[pydantic]'`` must be installed
  to use external views feature.


How it works?
-------------

Basically, the whole idea is that we **don't touch
the view logic / OpenAPI metadata in any way**.

The view itself can do any logic, parse / serialize objects in any way.
We also don't check the OpenAPI metadata in any way, except the type itself.

OpenAPI
~~~~~~~

Imagine that you already have an OpenAPI spec,
it might be from another library, old project, legacy service, etc.

But, we can continue to use it. Here's the one for the demo.

.. literalinclude:: /examples/external_views/openapi.yml
  :caption: openapi.yml
  :language: yaml
  :linenos:

Next, let's show how we can adapt any Django view to use this schema:

- both functional,
- and class-based.

Functional example
~~~~~~~~~~~~~~~~~~

Let's start with functions. Imagine that this is the function you want to reuse.
For example, this is a part of the legacy project that you actively rewrite.

.. literalinclude:: /examples/external_views/functions.py
  :caption: views.py
  :language: python
  :linenos:

Notice that ``/api/numbers`` path item definition from ``openapi.yml``
was inserted into our final schema as-is.

Class example
~~~~~~~~~~~~~

Now, the same, but with a class. It can be any ``View`` compatible class!

.. literalinclude:: /examples/external_views/classes.py
  :caption: views.py
  :language: python
  :linenos:


Registering OpenAPI schemas
---------------------------

Now, we have a new OpenAPI file.
It has two path parameters and also defines OpenAPI schemas
that we need to register, so they would be available in the final one:

.. literalinclude:: /examples/external_views/openapi2.yml
  :caption: openapi.yml
  :language: yaml
  :linenos:

To register OpenAPI schema components, we can use
:meth:`dmr.openapi.OpenAPIContext.register_external_components`:

.. literalinclude:: /examples/external_views/components.py
  :caption: views.py
  :language: python
  :linenos:

There are several rules on how we merge components:

- When trying to redefine an existing component by name,
  :exc:`ValueError` is raised
- We merge all components from all possible types
- We can't detect unused ones, so we merge all,
  even if some of them are not used


Real world use-cases
--------------------

For example, one can reuse:

- ``django-allauth`` `headles views <https://github.com/pennersr/django-allauth/tree/main/allauth/headless>`_
  that are built to be used by the pure Django framework
- Any ``APIView`` objects from ``django-rest-framework``
- Any ``ControllerBase`` objects from ``django-ninja-extra``
- And many more!
