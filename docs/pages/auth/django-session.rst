Django Session Auth
===================

Docs: https://docs.djangoproject.com/en/dev/topics/auth


Requiring auth
--------------

.. note::

  Current user will always be accessible as ``self.request.user``.

  Read more: https://docs.djangoproject.com/en/stable/topics/auth/default/

We provide two classes to require Django session auth in your API:

- :class:`~dmr.security.django_session.auth.DjangoSessionSyncAuth`
  for sync views
- :class:`~dmr.security.django_session.auth.DjangoSessionAsyncAuth`
  for async views

Example, how to use the auth class and how to get ``self.request.user``:

.. literalinclude:: /examples/auth/django_session/using_django_session.py
  :caption: views.py
  :linenos:
  :language: python

.. note::

  Using any of these classes would also automatically enable ``CSRF`` checks
  for this view. Because it is not secure to use Django
  session auth without ``CSRF`` checks.


Reusing pre-existing views
--------------------------

We provide several pre-existing views to get Django session cookie.
So, users won't have to write tons of boilerplate code.

We provide two :ref:`reusable-controllers` to obtain
Django session cookie:

1. :class:`~dmr.security.django_session.views.DjangoSessionSyncController`
   for sync controllers
2. :class:`~dmr.security.django_session.views.DjangoSessionAsyncController`
   for async controllers

To use them, you will need to:

1. Provide actual types for serializer, request model, and response body
2. Redefine
   :meth:`~dmr.security.django_session.views.DjangoSessionSyncController.convert_auth_payload`
   to convert your request model into the kwargs
   of :func:`django.contrib.auth.authenticate` to authenticate your request
3. Redefine
   :meth:`~dmr.security.django_session.views.DjangoSessionSyncController.make_api_response`
   to return the response in the format of your choice

.. literalinclude:: /examples/auth/django_session/django_session.py
  :caption: views.py
  :linenos:
  :language: python

Any further customizations are also possible.


CSRF
~~~~

When a user logs in through these controllers, Django automatically rotates
the CSRF token and includes a ``csrftoken`` cookie in the login response
(alongside the session cookie).

Clients making subsequent non-safe requests (``POST``, ``PUT``, ``PATCH``,
``DELETE``) to session-protected endpoints must send this token back via the
``X-CSRFToken`` request header.

.. note::

  When ``CSRF_USE_SESSIONS`` is ``True``, Django stores the CSRF token
  in the session instead of a cookie.  In that case no ``csrftoken`` cookie
  appears in the login response — the token is already embedded in the
  session used for authentication.

  See also:
    https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-CSRF_USE_SESSIONS


API Reference
-------------

.. autoclass:: dmr.security.django_session.auth.DjangoSessionSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.django_session.auth.DjangoSessionAsyncAuth
  :members:
  :inherited-members:

Pre-defined views to get Django session cookie
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.security.django_session.views.DjangoSessionSyncController
  :members:

.. autoclass:: dmr.security.django_session.views.DjangoSessionAsyncController
  :members:

.. autoclass:: dmr.security.django_session.views.DjangoSessionPayload
  :members:

.. autoclass:: dmr.security.django_session.views.DjangoSessionResponse
  :members:
