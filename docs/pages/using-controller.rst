Using Controller
================


.. _meta:

Defining OPTIONS or meta method
-------------------------------

`RFC 9110 <https://www.rfc-editor.org/rfc/rfc9110.html#name-options>`_
defines the ``OPTIONS`` HTTP method, but sadly Django's
:class:`~django.views.generic.base.View` which we use as a base class
for all controllers, already have
:meth:`django.views.generic.base.View.options` method.

It would generate a typing error to redefine it with a different
signature that we need for our endpoints.

That's why we created ``meta`` controller method as a replacement
for older ``options`` name.

To use it you have two options:

1. Define the ``meta`` endpoint yourself and provide an implementation
2. Use :class:`~django_modern_rest.options_mixins.MetaMixin`
   or :class:`~django_modern_rest.options_mixins.AsyncMetaMixin`
   with the default implementation: which provides ``Allow`` header
   with all the allowed HTTP methods in this controller

Here's an example of a custom ``meta`` implementation:

.. literalinclude:: /examples/using_controller/custom_meta.py
  :caption: views.py
  :linenos:
  :lines: 10-


See how you can use :ref:`composed-meta`
with :func:`~django_modern_rest.routing.compose_controllers`.


Next up
-------

.. grid:: 1 1 2 2
    :class-row: surface
    :padding: 0
    :gutter: 2

    .. grid-item-card:: :octicon:`comment-discussion` Returning responses
      :link: returning-responses
      :link-type: doc

      Learn how you can return a response from your endpoint.

    .. grid-item-card:: :octicon:`git-merge-queue` Routing
      :link: routing
      :link-type: doc

      Learn how routing works.
