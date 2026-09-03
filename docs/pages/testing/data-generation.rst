Preparing test data
===================

The arrange phase prepares the input and application state required by a test.
Good test data makes the scenario obvious: values that affect the behavior are
explicit, while incidental values require as little maintenance as possible.

Choose the simplest preparation strategy that communicates the test's intent:

.. list-table::
  :header-rows: 1
  :widths: 25 35 40

  * - Strategy
    - Use it when
    - Benefit
  * - Explicit values
    - A particular value is part of the scenario.
    - The important conditions are visible directly in the test.
  * - Fixtures
    - Several tests need the same object or application state.
    - Reusable setup stays separate while dependencies remain visible in the
      test signature.
  * - Faker
    - A field needs a valid value, but its exact value is irrelevant.
    - Tests can exercise a wider range of inputs without hand-written samples.
  * - Model factories
    - A complete structured object would be tedious to construct manually.
    - Valid data is generated from the same model that defines the API contract.

.. tip::

  Generated data is not automatically better than explicit data. Keep values
  that explain the scenario fixed, and generate only the details that are not
  relevant to the behavior under test. When choosing a model factory, consult
  the full `Polyfactory usage documentation`_ for all available features.


Start with explicit values
--------------------------

Prefer a small dictionary or model instance when all relevant fields fit
comfortably in the test. This makes the arrange phase readable without jumping
to a fixture or factory definition.

.. literalinclude:: /examples/testing/pytest_request_factory.py
  :caption: test_user_create.py
  :language: python
  :linenos:

In this example, the email and age describe the exact request being tested.
There is no benefit in generating them because the setup is already short and
clear.


Generate structured data from models
------------------------------------

As request models grow, keeping every valid field in each test becomes noisy
and makes schema changes expensive. `Polyfactory`_ can build data from
``pydantic``, ``msgspec``, ``@dataclass``, and ``TypedDict`` models.

Suppose the controller uses these ``pydantic`` models:

.. literalinclude:: /examples/testing/pydantic_controller.py
  :caption: views.py
  :language: python
  :linenos:

The same request model can define the factory used by the test:

.. literalinclude:: /examples/testing/polyfactory_usage.py
  :caption: test_user_create.py
  :language: python
  :linenos:

The important parts are:

1. Choose the factory base that matches the model type.
2. Set ``__check_model__ = True`` so generated values are validated against the
   model.
3. Use ``build()`` when you need a model instance without persisting anything.
4. Override fields that define the scenario and let the factory fill in the
   incidental fields.
5. Serialize the resulting model in the same representation accepted by the
   API.

.. tip::

  This example intentionally covers only the basic workflow. See the complete
  `Polyfactory usage documentation`_ for supported model types, field
  customization, constraints, nested factories, persistence handlers, and
  other available features.


Keep the arrange phase focused
------------------------------

Test setup should contain only what is needed to reach the behavior under test:

1. Make values involved in the expected behavior explicit.
2. Generate valid values for fields whose exact contents do not matter.
3. Use fixtures for genuinely shared setup or application state, not merely to
   hide a few local values.
4. Override generated values at the test site when they explain why the case is
   interesting.
5. Avoid assertions that depend on a specific random value. Assert the stable
   result or describe dynamic output with an appropriate matcher instead.

After arranging the input and executing the behavior, see
:doc:`Test assertions <assertions>` for choosing between exact snapshots and
matchers for dynamic values.

.. _Polyfactory: https://polyfactory.litestar.dev/latest/usage/index.html
.. _Polyfactory usage documentation: https://polyfactory.litestar.dev/latest/usage/index.html
