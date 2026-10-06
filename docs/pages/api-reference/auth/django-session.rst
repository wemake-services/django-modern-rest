Django Session Auth
===================

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
