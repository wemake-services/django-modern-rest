Testing tools
=============

Clients and helpers
-------------------

.. autoclass:: dmr.test.DMRRequestFactory
  :members:

.. autoclass:: dmr.test.DMRAsyncRequestFactory
  :members:

.. autoclass:: dmr.test.DMRClient
  :members:

.. autoclass:: dmr.test.DMRAsyncClient
  :members:

Auth
~~~~

.. autofunction:: dmr.test.disabled_auth

Throttling
~~~~~~~~~~

.. autofunction:: dmr.test.reduced_throttling

.. autofunction:: dmr.test.assert_throttled

.. autofunction:: dmr.test.assert_throttling

.. autofunction:: dmr.test.assert_async_throttling

pytest plugin
-------------


Clients:

.. autofunction:: dmr_pytest.dmr_client

.. autofunction:: dmr_pytest.dmr_async_client

Request factories:

.. autofunction:: dmr_pytest.dmr_rf

.. autofunction:: dmr_pytest.dmr_async_rf

Settings:

.. autofunction:: dmr_pytest.dmr_clean_settings

This fixture shadows the default one from `pytest-django`_:

.. autofunction:: dmr_pytest.settings

.. _pytest-django: https://github.com/pytest-dev/pytest-django
