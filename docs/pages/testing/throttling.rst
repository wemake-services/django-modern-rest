.. _testing-throttling:

Testing throttling
==================

We believe that throttling is a part of the business requirements,
so it must be tested. To help users with it, we provide several utilities:

- For sync controllers: :func:`dmr.test.assert_throttling`
- For async controllers: :func:`dmr.test.assert_async_throttling`

Testing that an endpoint is throttled usually means driving it to its limit
first. Sending the configured ``max_requests`` in a loop is slow for large
rates such as ``1000/hour``. What do we do instead?

1. We lower the ``max_requests`` value for the first throttle
   and increase the rate to be a hour. This way we can reliably
   and fastly test the expected behavior
2. Next, we send several requests (``max_requests`` controls this)
   that will hit the endpoint,
   assert that the response status matches ``success_status`` code
3. Lastly, we assert that the final request hits the rate limit,
   we also assert that the headers match our modified rate limit

Examples:

.. tabs::

  .. tab:: :iconify:`devicon:python` unittest

    Default Python's testing framework:

    .. literalinclude:: /examples/testing/throttling_unittest.py
      :caption: tests/test_throttling.py
      :linenos:
      :language: python

  .. tab:: :iconify:`devicon:pytest` pytest

    And more preferable ``pytest``:

    .. literalinclude:: /examples/testing/throttling_pytest.py
      :caption: test_reports.py
      :linenos:
      :language: python

Only the endpoint under test is affected; its throttling is restored afterwards.

There's also a lower level API:

- :func:`dmr.test.reduced_throttling` to reduce the throttle number manually
- :func:`dmr.test.assert_throttled` to assert that the response
  object is from throttling middleware
