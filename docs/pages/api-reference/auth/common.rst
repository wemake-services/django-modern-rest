How authentication works
========================

.. autoclass:: dmr.security.SyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.AsyncAuth
  :members:
  :inherited-members:

.. autoclass:: dmr.security.SyncOrAsyncAuth
  :members:

.. autofunction:: dmr.security.request_auth

.. autofunction:: dmr.security.add_www_authenticate

.. autodata:: dmr.security.NO_STORE_HEADERS

.. autoclass:: dmr.security.AuthenticatedHttpRequest
  :members:

Security
--------

CSRF
~~~~

.. autoclass:: dmr.security.csrf.CSRFSemanticSchemaProvider
  :members:

.. autofunction:: dmr.security.csrf.build_csrf_handler

.. autofunction:: dmr.security.csrf.csrf_message

.. autofunction:: dmr.security.csrf.csrf_response_spec

.. autofunction:: dmr.security.csrf.csrf_security_scheme

.. autoclass:: dmr.security.csrf.CSRFAuthMixin
  :members:

Semantic schema
---------------

.. autoclass:: dmr.semantic_schema.SecurityProvider
  :members:

.. autoclass:: dmr.semantic_schema.ResponseValidationSpecProvider
  :members:

.. autoclass:: dmr.semantic_schema.SecurityRequirementMerger
  :members:

.. autoclass:: dmr.semantic_schema.OrSecurityRequirementMerger
  :members:
