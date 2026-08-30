API Reference
=============

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
