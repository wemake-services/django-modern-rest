Testing
=======

Built-in testing tools
----------------------

Django has really good testing tools:

- https://docs.djangoproject.com/en/stable/topics/testing/tools
- https://docs.djangoproject.com/en/stable/topics/testing/advanced

Just like Django itself, we provide several built-in utilities for testing.

These includes subclasses of :class:`django.test.RequestFactory`
for sync and async requests. Use them for faster and simpler unit-tests:

- :class:`~dmr.test.DMRRequestFactory` for sync cases
- :class:`~dmr.test.DMRAsyncRequestFactory` for async ones

We also have two subclasses of :class:`django.test.Client`

- :class:`~dmr.test.DMRClient` for sync cases
- :class:`~dmr.test.DMRAsyncClient` for async ones

What is the difference between the default ones? Not much:

- Default ``Content-Type`` header is set to ``application/json``
- It is now easier to change ``Content-Type`` header as simple as specifying
  ``headers={'Content-Type': 'application/xml'}`` to change the content type
  for XML (or any other) requests and responses
- Our test clients are faster, because they use ``msgspec``
  if it is available to dump and parse json, instead of a regular :mod:`json`


Testing styles support
----------------------

We support both:

- :class:`django.test.TestCase` styled tests
- And `pytest-django <https://pytest-django.readthedocs.io/en/latest>`_
  styled tests

For ``pytest`` we also have a bundled plugin with several different fixtures:

.. literalinclude:: ../../dmr_pytest/__init__.py
  :caption: dmr_pytest/__init__.py
  :language: python
  :linenos:

No need to configure anything, just use these fixtures by names in your tests.

The fixtures that return callables also have public types in ``dmr_pytest``,
so you can annotate them in your own tests: ``ReducedThrottlingFixture``,
``AssertThrottledFixture``, ``AssertThrottlingFixture``, and
``AssertAsyncThrottlingFixture``. They are protocols that spell out the full
signature of the helper they provide, so calls are fully type-checked.
Fixtures returning objects, like ``dmr_client``, are annotated
with their regular types from ``dmr.test``.

You can use plain Django test primitives:

.. literalinclude:: /examples/testing/django_builtin_client.py
  :caption: django_builtin_client.py
  :language: python
  :linenos:

Or use ``dmr.test`` helpers when you want JSON defaults and controller-level
testing with request factories:

.. literalinclude:: /examples/testing/dmr_helpers.py
  :caption: dmr_helpers.py
  :language: python
  :linenos:


.. _testing-throttling:

Testing throttling
------------------

Testing that an endpoint is throttled usually means driving it to its limit
first. Sending the configured ``max_requests`` in a loop is slow for large
rates such as ``1000/hour``.

Instead, use ``assert_throttling`` from ``dmr.test``: it temporarily lowers the
endpoint's first throttle to a small ``max_requests`` (``2`` by default), drives
that many allowed requests plus one more, and asserts the ``429`` -- exercising
the full request cycle with a genuine response and headers. It returns the
rejected response so you can make further header assertions. Use
``assert_async_throttling`` for async controllers.

Both drivers take ``line`` to target the before-auth or after-auth throttle
line, and ``detail=False`` to skip the ``ratelimit`` body check when your
project uses a custom error model.

For finer control -- custom bodies or auth, or asserting exact headers -- pair
the underlying ``reduced_throttling`` context manager with ``assert_throttled``.
Both forms are shown here (the second test uses the context manager):

.. tabs::

  .. tab:: :iconify:`devicon:python` unittest

    .. literalinclude:: /examples/throttling/testing.py
      :caption: test_reports.py
      :linenos:
      :language: python

  .. tab:: :iconify:`devicon:pytest` pytest

    Our bundled plugin ships the same helpers as ``dmr_*`` fixtures, and
    ``dmr_pytest`` exports their types, so the fixtures can be annotated:

    .. literalinclude:: /examples/throttling/testing_pytest.py
      :caption: test_reports.py
      :linenos:
      :language: python

Only the endpoint under test is affected; its throttling is restored afterwards.

Header names are never hardcoded. Which headers are reported depends on the
throttle's :class:`~dmr.throttling.headers.BaseResponseHeadersProvider`
instances, so ``assert_throttled`` takes the ``throttle`` itself and checks
that every header its providers report is present -- be it
:class:`~dmr.throttling.headers.XRateLimit`,
:class:`~dmr.throttling.headers.RateLimitIETFDraft`, or your own provider.
The drivers pass the reduced throttle for you. Expected values go
into ``headers`` by name, as an ``int``, a ``str``, or a matcher::

    assert_throttled(response, headers={'RateLimit': IsStr()})

.. note::

  Lowering ``max_requests`` alone would not be enough for short windows: a
  ``2/second`` throttle resets between the driven requests, so the endpoint
  would never be rejected. That is why the reduced copy also gets an
  hour-long window -- every request a test sends lands inside the same
  window, whatever the endpoint's configured rate is.

  Mind this when asserting headers: ``X-RateLimit-Reset`` and ``Retry-After``
  report the widened window, not the rate you configured. And since they are
  computed from the current time, freeze it -- with
  `freezegun <https://github.com/spulec/freezegun>`_ or the ``freezer``
  fixture of `pytest-freezer <https://github.com/pytest-dev/pytest-freezer>`_
  -- when you assert their exact values; otherwise use a matcher such as
  ``dirty_equals.IsStr()``.


Structured data generation
--------------------------

Since ``django-modern-rest`` is already built around an idea
that we use models for everything, it is quite natural to reuse
these models for tests as well.

For example, one can use
`Polyfactory <https://polyfactory.litestar.dev/latest/>`_
to build test data from ``pydantic``, ``msgspec``,
``@dataclass``, or even ``TypedDict`` models.

Let's say you have this code for your controller, using ``pydantic`` models:

.. literalinclude:: /examples/testing/pydantic_controller.py
  :caption: views.py
  :language: python
  :linenos:

Let's reuse the models for data generation in tests!

.. literalinclude:: /examples/testing/polyfactory_usage.py
  :caption: test_user_create.py
  :language: python
  :linenos:

Which will make your tests simple, fast,
and will help you find unexpected corner cases.


Property-based API testing
--------------------------

There's a great tool called
`schemathesis <https://github.com/schemathesis/schemathesis>`_
that can be used to test your API to match your OpenAPI spec.

Official docs: https://schemathesis.readthedocs.io

``schemathesis`` is not bundled together with the ``django-modern-rest``.
You have to install it with:

.. tabs::

  .. tab:: :iconify:`material-icon-theme:uv` uv

    .. code-block:: bash

      uv add --group dev schemathesis

  .. tab:: :iconify:`devicon:poetry` poetry

    .. code-block:: bash

      poetry add --group dev schemathesis

  .. tab:: :iconify:`devicon:pypi` pip

    .. code-block:: bash

      pip install schemathesis


Now, let's see how you can generate thousands of tests for your API
with just several lines of python code:

.. literalinclude:: ../../tests/test_integration/test_openapi/test_schema.py
  :caption: tests/test_integration/test_openapi/test_schema.py
  :language: python
  :linenos:

What will happen here?

1. ``schemathesis`` loads OpenAPI schema definition
   from the ``reverse('openapi')`` URL
2. Then we will create a top level ``schema`` object from the ``api_schema``
   pytest fixture. It is needed to create a property-based test case
3. Lastly, we create a generated test case with
   the help of ``@schema.parametrize()``

You can also provide settings, like
the number of generated tests, enabled rules, auth, etc:

.. literalinclude:: ../../schemathesis.toml
  :caption: schemathesis.toml
  :language: toml
  :linenos:

When running the test case with

.. code-block:: bash

    pytest tests/test_integration/test_openapi/test_schema.py

it will cover all your API. In simple cases it might be enough tests.
Yes, you heard right: in simple cases just using ``schemathesis``
can remove the need to write any other integration tests.

.. important::

  Using ``schemathesis`` with ``django-modern-rest`` is very easy,
  because we offer state-of-the-art OpenAPI schema generation.
  It will be really hard to satisfy ``schemathesis`` with a different framework.


Validating responses
~~~~~~~~~~~~~~~~~~~~

``schemathesis`` can also be used in regular
tests to validate the response schema.
See https://schemathesis.readthedocs.io/en/stable/guides/schema-conformance/

Example:

.. code-block:: python

    from dmr.test import DMRClient

    def test_with_conditional_logic(dmr_client: DMRClient) -> None:
        response = dmr_client.post(
           '/users',
           data={'name': 'Alice'},
       )

       assert schema['/users']['POST'].is_valid_response(response.json())


API coverage with TraceCov
--------------------------

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most coverage tools measure which lines and branches of your implementation were
executed. TraceCov instead measures coverage of your API **contract**:
which OpenAPI operations, parameters, and response variants were exercised.

This matters because "missing contract coverage" often turns into real bugs:
edge cases for parameters, incorrect status codes, or response variants that your
tests never actually reach. With ``django-modern-rest`` the OpenAPI schema is
built from the project's :doc:`semantic schema <openapi/schema>` (derived from
:ref:`response validation <response_validation>`). That makes TraceCov coverage
tightly aligned with what your implementation claims to support.


Configuration
~~~~~~~~~~~~~

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

.. literalinclude:: ../../tests/test_integration/conftest.py
  :caption: conftest.py
  :language: python
  :linenos:
  :no-imports-spoiler:
  :lines: 1-13
  :emphasize-lines: 2, 13

To enable TraceCov recording for ``schemathesis`` runs, make sure your
``schemathesis`` test explicitly records validated interactions into
``tracecov_map`` via ``record_schemathesis_interactions(...)``.

.. literalinclude:: ../../tests/test_integration/test_openapi/test_schema.py
  :caption: test_schema.py
  :language: python
  :linenos:
  :no-imports-spoiler:
  :lines: 24-44
  :emphasize-lines: 5, 17

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
