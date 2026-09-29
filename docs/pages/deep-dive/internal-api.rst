Internal API
============

API documented here is not public, it can change at any time.
Please, do not use it directly.

However, it is documented so people and LLMs can better understand the code.


Middleware wrappers
-------------------

.. autoclass:: dmr.internal.middleware_wrapper.DecoratorWithResponses
  :members:


CSRF helpers
------------

.. autofunction:: dmr.internal.csrf.ensure_csrf


Json backends
-------------

.. autoclass:: dmr.internal.json.JsonModule
  :members:

.. autoclass:: dmr.internal.json.NativeJson
  :members:


Routing helpers
---------------

.. autoclass:: dmr.internal.routing.RouterMetadata
  :members:


Typing helpers
--------------

.. autodata:: dmr.internal.types.StrOrPromise
