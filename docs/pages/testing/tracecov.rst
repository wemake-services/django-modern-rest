API coverage with TraceCov
==========================

`TraceCov <https://docs.tracecov.sh/>`_ can be used as an optional API
coverage layer for ``django-modern-rest`` test suites. It complements regular
integration tests and ``schemathesis`` runs by showing which OpenAPI operations
and parameters were actually exercised.

Official docs: https://docs.tracecov.sh/

.. note::

  TraceCov is not bundled with the ``django-modern-rest``.
  You have to install it.

.. tabs::

  .. tab:: :iconify:`material-icon-theme:uv` uv

    .. code-block:: bash

        uv add --group dev tracecov

  .. tab:: :iconify:`devicon:poetry` poetry

    .. code-block:: bash

        poetry add --group dev tracecov

  .. tab:: :iconify:`devicon:pypi` pip

    .. code-block:: bash

        pip install tracecov


Why is this better than regular coverage?
-----------------------------------------

Most coverage tools measure which lines and branches of your implementation were
executed. TraceCov instead measures coverage of your API **contract**:
which OpenAPI operations, parameters, and response variants were exercised.

This matters because "missing contract coverage" often turns into real bugs:
edge cases for parameters, incorrect status codes, or response variants that your
tests never actually reach. With ``django-modern-rest`` the OpenAPI schema is
built from the project's :doc:`semantic schema <../openapi/schema>` (derived from
:ref:`response validation <response_validation>`). That makes TraceCov coverage
tightly aligned with what your implementation claims to support.


Configuration
-------------

How is that wired with ``django-modern-rest``?

- ``tracecov_map`` enables tracking for the whole test run.
- When ``tracecov_map`` is active, any test that uses ``dmr_client`` or
  ``dmr_async_client`` is automatically included in the TraceCov report.
- If you also run ``schemathesis``, the ``schemathesis`` test records which
  validated requests and responses correspond to which OpenAPI operation,
  so the report can connect execution back to the spec.

To enable tracking, define a session-scoped ``tracecov_map`` fixture.
When ``tracecov_map`` is configured and TraceCov is installed, ``dmr_client``
and ``dmr_async_client`` automatically register requests in ``tracecov``.

.. literalinclude:: ../../../tests/test_integration/conftest.py
  :caption: conftest.py
  :language: python
  :linenos:
  :no-imports-spoiler:
  :lines: 12-22

To enable TraceCov recording for ``schemathesis`` runs, make sure your
``schemathesis`` test explicitly records validated interactions into
``tracecov_map`` via ``record_schemathesis_interactions(...)``.

.. literalinclude:: ../../../tests/test_integration/test_openapi/test_schema.py
  :caption: test_schema.py
  :language: python
  :linenos:
  :no-imports-spoiler:
  :lines: 112-

What will happen here?

1. ``schemathesis`` executes requests generated from your OpenAPI schema.
2. After each ``schemathesis`` request is validated, the integration calls
   ``record_schemathesis_interactions(...)`` to record which OpenAPI
   operation and parameters were exercised for that verified response.
3. Independently from ``schemathesis``, any requests performed through
   ``dmr_client`` or ``dmr_async_client`` are tracked automatically when
   ``tracecov_map`` is active.
4. TraceCov aggregates coverage across operations, parameters, keywords, and
   response coverage.

.. tip::

  If TraceCov is not installed, or when ``tracecov_map`` is missing or inactive,
  fixtures return regular DMR clients without tracking.

When running your tests:

.. code-block:: bash

  pytest tests/test_integration/test_openapi/test_schema.py

TraceCov generates a report in various formats. See `TraceCov <https://docs.tracecov.sh/>`_
docs for details on the generated coverage report.

.. image:: /_static/images/tracecov.png
  :alt: TraceCov view
  :align: center

In short: run ``schemathesis`` and regular integration tests together and get
one unified TraceCov view of what your test suite actually exercised.
