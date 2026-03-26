.. _meta:

Defining ``OPTIONS`` or ``meta`` method
=======================================

`RFC 9110 <https://www.rfc-editor.org/rfc/rfc9110.html#name-options>`_
defines the ``OPTIONS`` HTTP method, but sadly Django's
:class:`~django.views.generic.base.View` which we use as a base class
for all controllers, already has
:meth:`~django.views.generic.base.View.options` method.

It would generate a typing error to redefine it with a different
signature that we need for our endpoints.

That's why we created our own ``meta`` controller method as a replacement
for older Django's ``options`` name.

To use it you have two options:

1. Define the ``meta`` endpoint yourself and provide a custom implementation
2. Use :class:`~dmr.options_mixins.MetaMixin`
   or :class:`~dmr.options_mixins.AsyncMetaMixin`
   with the default implementation: we provide ``Allow`` header
   with all the allowed HTTP methods in this controller

Here's an example of a custom ``meta`` implementation:

.. literalinclude:: /examples/using_controller/custom_meta.py
  :caption: views.py
  :language: python
  :linenos:
