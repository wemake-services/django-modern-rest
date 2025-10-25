Core Concepts
=============

To learn ``django-modern-rest`` you have to learn just a couple of things:

.. glossary::

  Endpoint
    :class:`~django_modern_rest.endpoint.Endpoint`
    is a single API route. It is defined
    by its name – HTTP method – and its :term:`Metadata`, what response schema
    it returns, what status codes it can return, etc.

  Controller
    :class:`~django_modern_rest.controller.Controller`
    is a collection of one or more :term:`endpoints <Endpoint>`.
    Controller is defined by incoming data parsing.
    So, if some endpoints expect the same data – they might live
    in the same controller.

  Component
    Controllers parse data via components like
    :class:`~django_modern_rest.components.Body`
    or :class:`~django_modern_rest.components.Headers`.
    You can write your own components.

  Metadata
    A collection of all the things each :term:`Endpoint` accepts and returns.
    It is used for request parsing, response validation, and OpenAPI schema.

  Serializer
    :class:`~django_modern_rest.serialization.BaseSerializer` subclass
    that knows how to load and dump raw data into models.
    We have 2 bundled serializers in :ref:`plugins`\ : for ``pydantic``
    and ``msgspec``, you can write your own serializers for other libraries.

  Routing
    Routing is a mapping of URLs to controllers.
    If some controllers need the same URLs, but different data parsing, we can
    :func:`compose <django_modern_rest.routing.compose_controllers>` them.

Example:

.. literalinclude:: /examples/core_concepts/glossary.py
  :caption: views.py
  :linenos:
  :lines: 10-


.. _plugins:

Plugins
-------


Routing
-------


Maximum integration with Django
-------------------------------

Works best with `django-stubs <https://github.com/typeddjango/django-stubs>`_.
Read next: our :doc:`integrations` guide.
