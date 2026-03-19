Testing
=======

Built-in testing tools
----------------------

Django has really good testing tools:

- https://docs.djangoproject.com/en/latest/topics/testing/tools
- https://docs.djangoproject.com/en/latest/topics/testing/advanced

Just like Django itself, we provide several builtin utilities for testing.

Which includes subclasses of :class:`django.test.RequestFactory`
for sync and async requests. Use them for faster and simpler unit-tests:

- :class:`~dmr.test.DMRRequestFactory` for sync cases
- :class:`~dmr.test.DMRAsyncRequestFactory` for async ones

We also have two subclasses of :class:`django.test.Client`

- :class:`~dmr.test.DMRClient` for sync cases
- :class:`~dmr.test.DMRAsyncClient` for async ones

What is the difference with the default ones? Not much:

- Default ``Content-Type`` header is set to be ``application/json``
- It is now easier to change ``Content-Type`` header as simple as specifying
  ``headers={'Content-Type': 'application/xml'}`` to change the content type
  for xml requests / responses


Testing styles support
----------------------

We support both:

- :class:`django.test.TestCase` styled tests
- And `pytest-django <https://pytest-django.readthedocs.io/en/latest>`_
  styled tests

For ``pytest`` we also have a bundled plugin with several different fixtures:

.. literalinclude:: ../../dmr_pytest.py
  :caption: dmr_pytest.py
  :language: python
  :linenos:

No need to configure anything, just use these fixtures by names in your tests.

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


Structured data generation
--------------------------

Since ``django-modern-rest`` is already built around an idea
that we use models for everything, it is quite natural to reuse
these models for tests as well.

For example, one can use
`Polyfactory <https://polyfactory.litestar.dev/latest/>`_
to build test data from ``pydantic``, ``msgspec``,
``@dataclass``, or even ``TypedDict`` models.

Let's say you have this code for you controller, using ``pydantic`` models:

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


Now, let's see how you can generate thounds of tests for your API
with just several lines of python code:

.. literalinclude:: /../tests/test_integration/test_openapi/test_schema.py
  :caption: test_schema.py
  :language: python
  :linenos:

What will happen here?

1. ``schemathesis`` with load OpenAPI schema definition
   from the ``reverse('openapi')`` URL
2. Then we will create a top level ``schema`` object from the ``api_schema``
   pytest fixture. It is needed to create a property-based test case
3. Lastly, we create a generated test case with
   the help of ``@schema.parametrize()``

You can also provide settings, like
the number of generated tests, enabled rules, auth, etc:

.. literalinclude:: /../schemathesis.toml
  :caption: schemathesis.toml
  :language: toml
  :linenos:

When running the test case with

.. code-block:: bash

    pytest tests/test_integration/test_openapi/test_schema.py

it will cover all your API. In simple cases it might be enough of tests.
Yes, you heard right: in simple cases just using ``schemathesis``
can remove the need in writing any other integration tests.

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
