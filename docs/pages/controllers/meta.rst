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

1. Use :class:`~dmr.options_mixins.MetaMixin`
   or :class:`~dmr.options_mixins.AsyncMetaMixin`
   with the default implementation: we provide ``Allow`` header
   with all the allowed HTTP methods in this controller
2. Define the ``meta`` endpoint yourself and provide a custom implementation


Using pre-defined mixins
------------------------

We have two versions: for sync and async controllers.
Their features are identical:

.. tabs::

  .. tab:: sync

    .. literalinclude:: /examples/using_controller/meta_sync.py
      :caption: dtos.py
      :language: python
      :linenos:

  .. tab:: async

    .. literalinclude:: /examples/using_controller/meta_async.py
      :caption: views.py
      :language: python
      :linenos:

Both of them:

- Provide ``meta`` method sync or async
- Provide the same response spec for the OpenAPI schema


Custom meta implementation
--------------------------

Since our mixins do not anything magical, you can write our own version,
if you need a behavior change, for example.

Here's an example of a custom ``meta`` implementation:

.. literalinclude:: /examples/using_controller/meta_custom.py
  :caption: views.py
  :language: python
  :linenos:

You would need to:

- Define ``meta`` method (sync or async) with the desired implementation
- Provide the required response spec
