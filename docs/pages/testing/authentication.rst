Testing authentication
======================

Practice shows us that most API endpoints will be using some
form of :doc:`authentication <../auth/common>`.

There are two ways to test it with ``django-modern-rest``.

The correct way to test auth
----------------------------

We don't ship our own version of ``force_authenticate`` or similar functions.
Because auth is one of the most important parts of your app.
We must not ship any simple ways to bypass it easily.
In this case most users will just bypass it in their apps.

How do you test views with auth? By providing it!

.. literalinclude:: /examples/testing/test_view_with_auth.py
  :caption: test_view_with_auth.py
  :language: python
  :linenos:

In this test we:

- Create a real auth :class:`~dmr.security.token.app.models.Token` instance
- Provide a real request header
- Use real auth logic to authenticate the request

We test that our real auth works the way we want it to.

The faster way to test auth
---------------------------

.. versionadded:: 0.13.0

But, we don't always strictly need to test auth again and again.
Only several tests might be enough.
Especially, if this auth is rather slow
due to 3rd party HTTP requests or a lot of crypto computations.

To fix this, we have a special function / ``pytest`` fixture
to disabled the auth for some specific endpoint.

Here's how it can be used:

.. literalinclude:: /examples/testing/test_view_disabled_auth.py
  :caption: test_view_disabled_auth.py
  :language: python
  :linenos:

Use this approach together with our request factories.
Works for both ``pytest`` and ``unittest``.

Our design goals here are:

1. Provide a utility for a non-common use-case
2. Make sure it does not compromise / affect / have a single source
   code change in the real auth flow, so no security problems
   can actually happen in production

.. tip::

  Do not use :meth:`django.test.Client.force_login`,
  because it will use the default Django's login / auth logic,
  not ``django-modern-rest`` custom one.
