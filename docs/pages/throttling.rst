Throttling
==========

``django-modern-rest`` ships its own throttling
(also known as "rate limiting") mechanism.
Here's how everything works.

.. important::

  If you have an option not to use ratelimiting in Django,
  but to use it on the HTTP Proxy side, you should prefer the proxy.
  It is significantly faster and more secure.


Defining throttling
-------------------

We have two classes to define throttling:

- :class:`dmr.throttling.SyncThrottle` for sync endpoints
- :class:`dmr.throttling.AsyncThrottle` for async endpoints

We can define throttling on three different levels:

.. tabs::

  .. tab:: per endpoint

    .. literalinclude:: /examples/throttling/per_endpoint.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: per controller

    .. literalinclude:: /examples/throttling/per_controller.py
      :caption: views.py
      :linenos:
      :language: python

  .. tab:: per settings

    .. code-block:: python
      :caption: settings.py
      :linenos:

      >>> from dmr.settings import Settings, DMR_SETTINGS
      >>> from dmr.throttling import SyncThrottle, Rate

      >>> DMR_SETTINGS = {Settings.throttling: [SyncThrottle(5, Rate.minute)]}

Providing several throttling instances means that all of them must succeed.
When multiple throttling rules are defined
on different levels, their rules are joined.

For example:

.. literalinclude:: /examples/throttling/multiple.py
  :caption: views.py
  :linenos:
  :language: python

Will guard ``GET`` method with 2 throttling checks:

1. Not more than 1 request per minute
2. And not more than 5 requests per hour

.. important::




Customizing throttling
----------------------

Rates
~~~~~

:class:`~dmr.throttling.Rate` is passed as the second required
parameter to throttle classes. However, all values that you pass
are just numbers of seconds. So, you can fully customize throttling
timings by passing any amount of seconds that you wish:

.. code-block:: python
  :caption: settings.py
  :linenos:

  >>> from dmr.settings import Settings, DMR_SETTINGS
  >>> from dmr.throttling import SyncThrottle

    >>> DMR_SETTINGS = {
  ...     Settings.throttling: [
  ...          SyncThrottle(
  ...              max_requests=5,
  ...              durantion_in_seconds=10,
  ...          ),
  ...     ],
  ... }

This will set a throttling rule: no more than 5 requests in 10 seconds.

Backends
~~~~~~~~

Backends are used to define where we store throttling data.

By default we use :class:`dmr.throttling.backends.DjangoCache` as the backend.
You can customize which cache name is used. For example:

.. code-block:: python
  :caption: settings.py
  :linenos:

  >>> from dmr.settings import Settings, DMR_SETTINGS
  >>> from dmr.throttling import SyncThrottle, Rate
  >>> from dmr.throttling.backends import DjangoCache

  >>> DMR_SETTINGS = {
  ...     Settings.throttling: [
  ...          SyncThrottle(
  ...              max_requests=5,
  ...              durantion_in_seconds=Rate.second,
  ...              backend=DjangoCache(cache_name='throttling'),
  ...          ),
  ...     ],
  ... }

You can also write your own backends, for example,
to store throttling information in memory or somewhere else.
To do so, you would need to subclass
:class:`dmr.throttling.backends.BaseThrottleBackend`
and override 4 methods.

Full list of backends that we ship in ``django-modern-rest``:

- :class:`~dmr.throttling.backends.DjangoCache`

Algorithms
~~~~~~~~~~

Algorithms are used to define the logic of how requests are counted.

By default we use :class:`dmr.throttling.algorithms.SimpleRate`
as the algorithm.

You can also write your own algorithms.
To do so, you would need to subclass
:class:`dmr.throttling.algorithms.BaseThrottleAlgorithm`
and override 2 methods.

Full list of algorithms that we ship in ``django-modern-rest``:

- :class:`~dmr.throttling.algorithms.SimpleRate`

Cache keys
~~~~~~~~~~

Cache keys is what defines how requests are identified.

By default we use :func:`dmr.throttling.cache_keys.RemoteAddr` function,
which identifies requests by IP taken from
`RemoteAddr <https://docs.djangoproject.com/en/6.0/ref/request-response/#django.http.HttpRequest.META>`_
value from ``request.META``.

You can write your own cache keys, they are regular functions that accept
:class:`~dmr.endpoint.Endpoint` and :class:`~dmr.controller.Controller`
as arguments and return a string or ``None``.

If cache key returns ``None``, it means that no throttling
will be applied to this request. It is useful to skip some requests,
for example, from paid or superusers from throttling checks.

Full list of cache keys that we ship in ``django-modern-rest``:

- :class:`~dmr.throttling.cache_keys.RemoteAddr`

Headers
~~~~~~~

By default on ``429`` error we return three headers:

- ``RateLimit-Limit`` - The maximum number of requests permitted
  in the current time window
- ``RateLimit-Remaining`` - The number of requests remaining
  in the current time window
- ``RateLimit-Reset`` - The number of seconds until the current
  rate limit window resets

You can customize the prefix of these headers. Because some APIs still
use older ``X-RateLimit-Limit`` version with ``X-`` prefix.

To do so, you can use :attr:`~dmr.throttling.SyncThrottle.header_prefix`
attribute:

.. literalinclude:: /examples/throttling/header_prefix.py
  :caption: views.py
  :linenos:
  :language: python

When ``header_prefix`` is set to ``None``, these headers are disabled.

.. seealso::

  https://www.ietf.org/archive/id/draft-polli-ratelimit-headers-02.html

.. note::

  We don't support the latest draft
  https://www.ietf.org/archive/id/draft-ietf-httpapi-ratelimit-headers-10.html
  but, it can be easily done by overriding several methods by users how need it.

You can also customize whether
we should automatically add ``Retry-After`` header, which we add by default.
To disable this header, set
:attr:`~dmr.throttling.SyncThrottle.header_include_retry_after`
to ``False``:

.. literalinclude:: /examples/throttling/header_include_retry_after.py
  :caption: views.py
  :linenos:
  :language: python

.. seealso::

  https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Retry-After


Adding ratelimit headers to responses
-------------------------------------

.. literalinclude:: /examples/throttling/response_headers.py
  :caption: views.py
  :linenos:
  :language: python


Security
--------

Key considerations:

- Be sure to correctly setup your HTTP Proxy server to send correct IP headers
- Be especially careful with ``X-Forwarded-For`` header,
  because it can contain several layers of proxies
- Never rate limit on user supplied data such as ``User-Agent``,
  because this data can easily be changed
- Denial of service: be careful not to limit other users when limiting just one
- Do not store sensitive or personal users' data in your cache keys,
  because it is stored with no protection / encryption

.. seealso::

  https://django-ratelimit.readthedocs.io/en/latest/security.html


API Reference
-------------
