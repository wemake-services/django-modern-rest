Using sync and async code together
==================================

Writting sync code is easy, fun, and readable.
Writting async code is sometimes required:

- If you use HTTP requests to other services
- If you are using SSE or WebSockets
- etc

But, how can one use the best of two worlds?


Running everything under ASGI
-----------------------------

Django provides default ``asgi`` interface to run both async and sync views.

But, Django has to run a threadpool, emulate async mode
for sync views, and switch contexts.

This will come with a small performance penalty.

The same is true for sync / async middleware.

See:

- https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/uvicorn/
- https://docs.djangoproject.com/en/6.0/topics/async/#performance

This is supported in ``django-modern-rest``.


Separating sync from async
--------------------------

Another way is to run two instances of your app:

1. One with ``gunicorn`` and sync-only views and middleware
2. The second one with ``uvicorn`` and async-only views and middleware

``django-modern-rest`` does not allow mixing async
and sync endpoints in one controller just for this reason.

How to properly isolate these two applications?

1. Create two files for urls: ``urls.py`` for default sync mode
   and ``async_urls.py`` for async mode.
   Make sure that async urls have a unique ulr prefix: ``/async/``
2. Create two settings file (we recommend using
   `django-split-settings <https://github.com/wemake-services/django-split-settings>`_
   for that
3. In these two settings file specify two different
   `ROOT_URLCONF's <https://docs.djangoproject.com/en/6.0/ref/settings/#root-urlconf>`_,
   one for ``urls.py`` and one for ``async_urls.py``
4. Run two different instances of Django: one with ``gunicorn`` and ``urls.py``,
   one with ``uvicorn`` and ``async_urls.py``
5. In your proxy server route ``/async/`` url prefix to ``uvicorn``
   and all others to ``gunicorn``

Done.

Now async views with work in async runtime, while sync views
will work in sync runtime with minimal overhead.

This is supported in ``django-modern-rest``.
