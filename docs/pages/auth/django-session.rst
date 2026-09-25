Django Session Auth
===================

Docs: https://docs.djangoproject.com/en/dev/topics/auth

For this auth to work, you will need to:

1. Properly add and configure
   :class:`django.contrib.sessions.middleware.SessionMiddleware` middleware
2. Properly add and configure
   :class:`django.contrib.auth.middleware.AuthenticationMiddleware` middleware
3. Set correct auth settings, like enabling ``django.contrib.auth`` app

Make sure to follow the default Django's guide on setting up
the regular Django auth before going further.


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
  We automatically enforce CSRF checks before any other actions are taken.

Custom user models are automatically supported.

CSRF in auth
~~~~~~~~~~~~

We additionally require CSRF checks to pass on non-safe HTTP methods like
``POST``, ``PUT``, ``DELETE``, etc.

Security requirement generated for these methods will reflect that:
they will need both ``django_session`` and ``csrf`` security requirements
to be present for successful login.

.. seealso::

  - https://docs.djangoproject.com/en/stable/ref/csrf/


.. _django-session-concrete-views:

Ready-to-use views
------------------

A login endpoint that takes a username and a password
and starts a session is already written for you
in ``dmr.security.django_session.concrete_views``.
Name your serializer in the urls and you are done,
there is no view code at all:

.. literalinclude:: /examples/auth/django_session/django_session_concrete.py
  :caption: urls.py
  :linenos:
  :language: python

These are the very same controllers
as the ones in ``dmr.security.django_session.views``, with
:class:`~dmr.security.django_session.views.DjangoSessionPayload` and
:class:`~dmr.security.django_session.views.DjangoSessionResponse`
already plugged in as the request and response bodies.
Their ``as_view`` takes the fields they require as typed keyword
arguments and passes everything else to django as usual, see
:meth:`~dmr.security.django_session.concrete_views.DjangoSessionSyncController.as_view`.

They all set ``auth = None``: they are the very endpoints
that check credentials, so auth from the settings
must never be required to reach them.

.. tip::

  These should be your default for the common cases.
  Any custom logic belongs to the reusable controllers below instead:
  they are the same classes with the bodies and the hooks left open,
  so customize those rather than subclassing these.


Customizing pre-existing views
------------------------------

We provide several pre-existing views to get Django session cookie.
So, users won't have to write tons of boilerplate code.

Reach for them when the bodies of :ref:`django-session-concrete-views`
do not match your API.

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

CSRF in views
~~~~~~~~~~~~~

When a user logs in through these controllers, Django automatically rotates
the CSRF token and includes
a `CSRF cookie <https://docs.djangoproject.com/en/stable/ref/settings/#csrf-cookie-name>`_
in the login response (alongside the session cookie).

.. note::

  When ``CSRF_USE_SESSIONS`` is ``True``, Django stores the CSRF token
  in the session instead of a cookie.  In that case no ``csrftoken`` cookie
  appears in the login response — the token is already embedded in the
  session used for authentication.

.. seealso::

  - https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-CSRF_USE_SESSIONS


API Reference
-------------

.. autoclass:: dmr.security.django_session.auth.DjangoSessionSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.django_session.auth.DjangoSessionAsyncAuth
  :members:
  :inherited-members:

Ready-to-use views to get Django session cookie
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: dmr.security.django_session.concrete_views.DjangoSessionSyncController
  :members: as_view, convert_auth_payload, make_api_response

.. autoclass:: dmr.security.django_session.concrete_views.DjangoSessionAsyncController
  :members: as_view, convert_auth_payload, make_api_response

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
