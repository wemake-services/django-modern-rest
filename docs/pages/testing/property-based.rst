Property-based API testing
==========================

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

.. literalinclude:: ../../../tests/test_integration/test_openapi/test_schema.py
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

.. literalinclude:: ../../../schemathesis.toml
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
--------------------

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
