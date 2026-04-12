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

1. Not more ``<=`` than 1 request per minute
2. And not more ``<=`` than 5 requests per hour


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
  ...              duration_in_seconds=10,
  ...          ),
  ...     ],
  ... }

This will set a throttling rule: no more than 5 requests in 10 seconds.

Backends
~~~~~~~~

Backends are used to define where we store throttling data.

By default we use :class:`dmr.throttling.backends.DjangoCache` as the backend.
You can customize which cache name is used. For example:

.. literalinclude:: /examples/throttling/cache_customization.py
  :caption: views.py
  :linenos:
  :language: python

You can also write your own backends, for example,
to store throttling information in memory or somewhere else.
To do so, you would need to subclass
:class:`dmr.throttling.backends.BaseThrottleBackend`
and override 4 methods.

Full list of backends that we ship in ``django-modern-rest``:

- :class:`~dmr.throttling.backends.DjangoCache`, default

Algorithms
~~~~~~~~~~

Algorithms are used to define the logic of how requests are counted.

By default we use :class:`dmr.throttling.algorithms.SimpleRate`
as the algorithm.
It defines a fixed window with a fixed amount of requests possible.
When window is expired, it resets the count of requests.

You can also write your own algorithms.
To do so, you would need to subclass
:class:`dmr.throttling.algorithms.BaseThrottleAlgorithm`
and override 2 methods.

Full list of algorithms that we ship in ``django-modern-rest``:

- :class:`~dmr.throttling.algorithms.SimpleRate`, default

Cache keys
~~~~~~~~~~

Cache keys is what defines how requests are identified.

By default we use :func:`dmr.throttling.cache_keys.RemoteAddr` cache key,
which identifies requests by IP taken from
`REMOTE_ADDR <https://docs.djangoproject.com/en/6.0/ref/request-response/#django.http.HttpRequest.META>`_
value from ``request.META``.

.. warning::

  If you are using reverse proxies, make sure to correctly configure
  how they pass request headers, to ``REMOTE_ADDR`` would be correct.

You can write your own cache keys, they are subclasses
of :class:`~dmr.throttling.cache_keys.BaseThrottleCacheKey`
and must return a string or ``None``.

If cache key returns ``None``, it means that this request
will be skipped from this exact throttling check.
However, other keys may still be applied.

It is useful to skip some requests from throttling checks,
for example, from paid or stuff users.

Full list of cache keys that we ship in ``django-modern-rest``:

- :class:`~dmr.throttling.cache_keys.RemoteAddr`, default

When throttling is executed
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Throttling is executed in two stages: before auth and after auth.
Why? Because we need to:

1. Protect auth from abusive requests and brute forcing
2. Make sure we can base throttling rules on the auth info

.. mermaid::
  :caption: Throttling execution
  :config: {"theme": "forest"}

  graph
      Start[New request] --> BeforeThrottle[Throttling based on IP];
      BeforeThrottle --> Auth[Auth];
      Auth --> AfterThrottle[Throttling based on auth];

All cache keys know when to execute by default, however you can customize this.
For example, you can run some IP based throttling checks after the auth itself:

.. literalinclude:: /examples/throttling/throttling_after_auth.py
  :caption: views.py
  :linenos:
  :language: python

.. warning::

  It is **strongly** not recommended to have
  auth without any throttling before it.

  Auth must be protected from brute force and denial of service attacks!
  For example, one can also use
  `django-axes <https://github.com/jazzband/django-axes>`_ for this.

  `wemake-django-template <https://github.com/wemake-services/wemake-django-template>`_
  has this configured properly.

Note that it won't make any sense to run auth-based throttling before auth.
So, customize it with care.


Headers
~~~~~~~

By default on
`429 Too Many Requests <https://developer.mozilla.org/de/docs/Web/HTTP/Reference/Status/429>`_
error we return four headers:

- ``X-RateLimit-Limit`` - The maximum number of requests permitted
  in the current time window
- ``X-RateLimit-Remaining`` - The number of requests remaining
  in the current time window
- ``X-RateLimit-Reset`` - The number of seconds until the current
  rate limit window resets
- ``Retry-After`` - The number of seconds until the current
  rate limit window resets, see
  `RFC-6585 <https://datatracker.ietf.org/doc/html/rfc6585#section-4>`_
  and `RFC-7231 <https://datatracker.ietf.org/doc/html/rfc7231#section-7.1.3>`_

.. note::

  Headers with ``X-`` prefix means that they are custom ones,
  there's no spec behind them.
  However, this convention is the most popular one as of right now.

OpenAPI support is built in for this feature.
All headers classes will provide the proper
:class:`~dmr.headers.HeaderSpec` for the ``429`` response.

You might want to customize the returned headers. To do so,
you can pass ``response_headers`` argument to throttling classes
with header classes that you actually want to support.

For example, you can disable
`Retry-After <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Retry-After>`_
header with:

.. literalinclude:: /examples/throttling/header_disable_retry_after.py
  :caption: views.py
  :linenos:
  :language: python

Or if you want to support
the `latest draft <https://www.ietf.org/archive/id/draft-ietf-httpapi-ratelimit-headers-10.html>`_
about ``RateLimit`` and ``RateLimit-Policy`` headers, you can use:

.. literalinclude:: /examples/throttling/header_ietf_draft.py
  :caption: views.py
  :linenos:
  :language: python

You can also combine these headers with each other in any combinations.
You can write your own classes with custom headers support.
To do so, subclass :class:`dmr.throttling.headers.BaseResponseHeadersProvider`.

You can completely disable any extra response headers by passing an empty list.

Full list of header providers that we ship in ``django-modern-rest``:

- :class:`~dmr.throttling.headers.XRateLimit`, default
- :class:`~dmr.throttling.headers.RetryAfter`, default
- :class:`~dmr.throttling.headers.RateLimitIETFDraft`


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

Base
~~~~

.. autoclass:: dmr.throttling.SyncThrottle
  :members:
  :inherited-members:

.. autoclass:: dmr.throttling.AsyncThrottle
  :members:
  :inherited-members:

.. autoclass:: dmr.throttling.Rate
  :members:

Backends
~~~~~~~~

.. autoclass:: dmr.throttling.backends.CachedRateLimit
  :members:
  :show-inheritance:

.. autoclass:: dmr.throttling.backends.BaseThrottleBackend
  :members:

.. autoclass:: dmr.throttling.backends.DjangoCache
  :members:

Algorithms
~~~~~~~~~~

.. autoclass:: dmr.throttling.algorithms.BaseThrottleAlgorithm
  :members:

.. autoclass:: dmr.throttling.algorithms.SimpleRate
  :members:

Cache keys
~~~~~~~~~~

.. autoclass:: dmr.throttling.cache_keys.BaseThrottleCacheKey
  :members:

.. autoclass:: dmr.throttling.cache_keys.RemoteAddr
  :members:

Headers
~~~~~~~

.. autoclass:: dmr.throttling.headers.BaseResponseHeadersProvider
  :members:

.. autoclass:: dmr.throttling.headers.XRateLimit
  :members:

.. autoclass:: dmr.throttling.headers.RetryAfter
  :members:

.. autoclass:: dmr.throttling.headers.RateLimitIETFDraft
  :members:
