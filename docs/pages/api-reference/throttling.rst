Throttling
==========

Base
~~~~

.. autoclass:: dmr.throttling.SyncThrottle
  :members:
  :inherited-members:

.. autoclass:: dmr.throttling.AsyncThrottle
  :members:
  :inherited-members:

.. autoclass:: dmr.throttling.SyncOrAsyncThrottle
  :members:

.. autoclass:: dmr.throttling.Rate
  :members:

.. autoclass:: dmr.throttling.ThrottlingReport
  :members:

Backends
~~~~~~~~

.. autoclass:: dmr.throttling.backends.CachedRateLimit
  :members:
  :show-inheritance:

.. autoclass:: dmr.throttling.backends.BaseThrottleSyncBackend
  :members:

.. autoclass:: dmr.throttling.backends.BaseThrottleAsyncBackend
  :members:

.. autoclass:: dmr.throttling.backends.SyncDjangoCache
  :members:

.. autoclass:: dmr.throttling.backends.AsyncDjangoCache
  :members:

.. autoclass:: dmr.throttling.backends.django_cache.UnsafeCacheBackendWarning
  :members:

.. autoclass:: dmr.throttling.backends.redis.SyncRedis
  :members:

.. autoclass:: dmr.throttling.backends.redis.AsyncRedis
  :members:

Algorithms
~~~~~~~~~~

.. autoclass:: dmr.throttling.algorithms.BaseThrottleAlgorithm
  :members:

.. autoclass:: dmr.throttling.algorithms.SimpleRate
  :members:

.. autoclass:: dmr.throttling.algorithms.LeakyBucket
  :members:

Cache keys
~~~~~~~~~~

.. autoclass:: dmr.throttling.cache_keys.BaseThrottleCacheKey
  :members:

.. autoclass:: dmr.throttling.cache_keys.RemoteAddr
  :members:

.. autoclass:: dmr.throttling.cache_keys.UserPk
  :members:

.. autoclass:: dmr.throttling.cache_keys.JwtToken
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
