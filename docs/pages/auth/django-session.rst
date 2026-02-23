Django Session Auth
===================

Docs: https://docs.djangoproject.com/en/dev/topics/auth


Requiring auth
--------------

We provide two classes to require Django session auth in you API:

- :class:`~dmr.security.django_session.DjangoSessionSyncAuth` for sync views
- :class:`~dmr.security.django_session.DjangoSessionAsyncAuth` for async views

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


API Reference
-------------

.. autoclass:: dmr.security.django_session.DjangoSessionSyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.django_session.DjangoSessionAsyncAuth
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
