Core concepts
=============

To learn ``django-modern-rest`` you have to learn just a couple of things:

.. glossary::

  Endpoint
    :class:`~django_modern_rest.endpoint.Endpoint`
    is a single API route. It is defined
    by its name – HTTP method – and its :term:`Metadata`, what response schema
    it returns, what status codes it can return, etc.

  Blueprint
    :class:`~django_modern_rest.controller.Blueprint` is a building block
    for composition of different HTTP methods and parsing rules under
    one resulting URL.

  Controller
    :class:`~django_modern_rest.controller.Controller`
    is a collection of one or more :term:`endpoints <Endpoint>`
    with the same set of :term:`components <Component>`.
    Controller is a subclass of :class:`~django.views.generic.base.View`, so
    it can be used in a routing.
    Controller can also be composed of different :term:`blueprints <Blueprint>`,
    so different parsing rules can share one final URL.

  Component
    Controllers parse data via components like
    :class:`~django_modern_rest.components.Body`
    or :class:`~django_modern_rest.components.Headers`.
    You can write your own components.

  Metadata
    A collection of all the things each :term:`Endpoint` accepts and returns.
    It is used for request parsing, response validation, and OpenAPI schema.

  Serializer
    :class:`~django_modern_rest.serializer.BaseSerializer` subclass
    that knows how to load and dump raw data into models.
    We have 2 bundled serializers in :doc:`plugins <plugins>`\ :
    for ``pydantic`` and ``msgspec``, you can write your
    own serializers for other libraries.

  Routing
    Routing is a mapping of URLs to controllers.
    If some controllers need the same URLs, but different data parsing, we can
    :doc:`compose <routing>` them.

Example:

.. literalinclude:: /examples/core_concepts/glossary.py
  :caption: views.py
  :language: python
  :linenos:
  :lines: 10-


Async vs Sync
-------------

We support both Django modes: sync and async, the same way regular Django
`supports <https://docs.djangoproject.com/en/latest/topics/async/>`_ them.

We don't do anything special with the async mode, so any existing
guides, tools, deployment strategies should
just work with ``django-modern-rest`` if they work for Django.


Maximum integration with Django
-------------------------------

We try to keep Django compatibility as our main goal.
Everything should work by default, starting
from `django-cors-headers <https://pypi.org/project/django-cors-headers>`_
up to `django-ratelimit <https://pypi.org/project/django-ratelimit>`_.

We also provide :doc:`middleware` wrapper tools to convert any middleware
response to the required API schema and set needed ``Content-Type``, etc.

We support all existing mixins: because
:class:`~django_modern_rest.controller.Controller` is a subclass
of Django's :class:`django.views.generic.base.View` class.

We support all existing decorators: because we have
:func:`~django_modern_rest.decorators.endpoint_decorator`
and :func:`~django_modern_rest.decorators.dispatch_decorator` utilities
that can decorate endpoints and controllers.

Works best with `django-stubs <https://github.com/typeddjango/django-stubs>`_.
Read next: our :doc:`integrations` guide.


Next up
-------

.. grid:: 1 1 2 2
    :class-row: surface
    :padding: 0
    :gutter: 2

    .. grid-item-card:: :octicon:`rocket` Using Controller
      :link: using-controller
      :link-type: doc

      Learn how controllers work.

    .. grid-item-card:: :octicon:`gear` Configuration
      :link: configuration
      :link-type: doc

      Learn how to configure ``django-modern-rest``.
