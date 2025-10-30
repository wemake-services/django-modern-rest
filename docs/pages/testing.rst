Testing
=======

Built-in testing tools
----------------------

Django has really good testing tools:

- https://docs.djangoproject.com/en/latest/topics/testing/tools
- https://docs.djangoproject.com/en/latest/topics/testing/advanced

Just like Django itself, we provide several builtin utilities for testing.

Which includes subclasses of :class:`django.test.RequestFactory`
for sync and async requests. Use them for faster and simplier unit-tests:

- :class:`~django_modern_rest.test.DMRRequestFactory` for sync cases
- :class:`~django_modern_rest.test.DMRAsyncRequestFactory` for async ones

We also have two subclasses of :class:`django.test.Client`

- :class:`~django_modern_rest.test.DMRClient` for sync cases
- :class:`~django_modern_rest.test.DMRAsyncClient` for async ones

What is the difference with the default ones? Not much:

- Default ``Content-Type`` header is set to be ``application/json``
- It is now easier to change ``Content-Type`` header as simple as specifing
  ``headers={'Content-Type': 'application/xml'}`` to change the content type
  for xml requests / responses


Testing styles support
----------------------

We support both:

- :class:`django.test.TestCase` styled tests
- And `pytest-django <https://pytest-django.readthedocs.io/en/latest>`_
  styled tests

For ``pytest`` we also have a bundled plugin with 4 different fixtures:

.. literalinclude:: ../../django_modern_rest_pytest.py
  :caption: django_modern_rest_pytest.py
  :linenos:
  :lines: 21-

No need to configure anything, just use these fixtures by names in your tests.


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
  :linenos:
  :lines: 10-

Let's reuse the models for data generation in tests!

.. literalinclude:: /examples/testing/polyfactory_usage.py
  :caption: test_user_create.py
  :linenos:

Which will make your tests simple, fast,
and will help you find unexpected corner cases.
