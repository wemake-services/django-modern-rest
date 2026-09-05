Testing tools
=============

Django already provides a mature set of
`testing tools <https://docs.djangoproject.com/en/stable/topics/testing/tools>`_
and
`advanced testing utilities <https://docs.djangoproject.com/en/stable/topics/testing/advanced>`_.
``django-modern-rest`` builds on these primitives instead of replacing them.

It provides JSON-oriented request factories and test clients for both sync and
async code, together with a bundled ``pytest`` plugin. All DMR testing tools use
the same request API as their Django counterparts.


Choosing a tool
---------------

Choose the narrowest tool that exercises the behavior you need:

.. list-table::
  :header-rows: 1
  :widths: 25 25 50

  * - Tool
    - Test level
    - Use it when
  * - :class:`~dmr.test.DMRRequestFactory`
    - Sync unit test
    - You want to call a sync controller directly without URL routing or
      middleware.
  * - :class:`~dmr.test.DMRAsyncRequestFactory`
    - Async unit test
    - You want the same focused test for an async controller.
  * - :class:`~dmr.test.DMRClient`
    - Sync integration test
    - URL routing, middleware, and the complete Django request-response cycle
      are part of the behavior under test.
  * - :class:`~dmr.test.DMRAsyncClient`
    - Async integration test
    - You need the complete request-response cycle with an async test client.

Request factories are usually the fastest choice for focused controller tests.
Use a test client when routing, middleware, or another integration boundary
matters.


Request factories
-----------------

:class:`~dmr.test.DMRRequestFactory` extends
:class:`django.test.RequestFactory` and creates WSGI requests.
:class:`~dmr.test.DMRAsyncRequestFactory` extends
:class:`django.test.AsyncRequestFactory` and creates ASGI requests.

Like Django request factories, they create a request object but do not send it
through URL routing or middleware. Pass the request directly to
``Controller.as_view()`` instead. For async controllers, create the request
synchronously and await the controller response. Use
``DMRAsyncRequestFactory.wrap()`` when static type checkers need help
understanding that the controller returns an awaitable.

The following tabs test the same controller with Django's request factory,
DMR's request factory, and the DMR ``pytest`` fixture:

.. tabs::

  .. tab:: :iconify:`devicon:python` unittest with Django primitives

    .. literalinclude:: /examples/testing/django_request_factory.py
      :caption: django_request_factory.py
      :language: python
      :linenos:

  .. tab:: :iconify:`devicon:python` unittest with DMR primitives

    .. literalinclude:: /examples/testing/dmr_request_factory.py
      :caption: dmr_request_factory.py
      :language: python
      :linenos:

  .. tab:: :iconify:`devicon:pytest` pytest

    The ``dmr_rf`` fixture provides a fresh
    :class:`~dmr.test.DMRRequestFactory`.

    .. literalinclude:: /examples/testing/pytest_request_factory.py
      :caption: pytest_request_factory.py
      :language: python
      :linenos:


Test clients
------------

:class:`~dmr.test.DMRClient` extends :class:`django.test.Client`, while
:class:`~dmr.test.DMRAsyncClient` extends :class:`django.test.AsyncClient`.
Unlike request factories, test clients resolve the requested URL and execute
the Django middleware chain.

This makes them a better fit for integration tests. The following tabs exercise
the same endpoint with Django's client, DMR's client, and the DMR ``pytest``
fixture:

.. tabs::

  .. tab:: :iconify:`devicon:python` unittest with Django primitives

    .. literalinclude:: /examples/testing/django_test_client.py
      :caption: django_test_client.py
      :language: python
      :linenos:

  .. tab:: :iconify:`devicon:python` unittest with DMR primitives

    .. literalinclude:: /examples/testing/dmr_test_client.py
      :caption: dmr_test_client.py
      :language: python
      :linenos:

  .. tab:: :iconify:`devicon:pytest` pytest

    The ``dmr_client`` fixture provides a fresh :class:`~dmr.test.DMRClient`.

    .. literalinclude:: /examples/testing/pytest_test_client.py
      :caption: pytest_test_client.py
      :language: python
      :linenos:

Async tools
-----------

For async tests, use :class:`~dmr.test.DMRAsyncRequestFactory` or
:class:`~dmr.test.DMRAsyncClient`. Their ``pytest`` equivalents are
``dmr_async_rf`` and ``dmr_async_client``. Calls made with the async client and
async controller responses must be awaited.

The DMR ``pytest`` plugin is registered automatically when `pytest-django`_ is
installed; no ``conftest.py`` configuration is required. See the
:doc:`pytest plugin API reference <api-reference>` for all available fixtures.


Sending data and checking responses
-----------------------------------

JSON requests
~~~~~~~~~~~~~

DMR request factories and clients use ``application/json`` as the default
``Content-Type`` for requests with a body. Dictionaries, lists, and other
JSON-compatible values passed as ``data`` are serialized automatically. The
DMR examples above rely on this default.

When ``msgspec`` is installed, DMR uses it to serialize request data and parse
JSON responses. Otherwise, it falls back to Python's :mod:`json` implementation.
Strings and bytes are treated as already encoded and are not serialized again.

Custom content types
~~~~~~~~~~~~~~~~~~~~

Pass ``content_type`` when the request body uses a different representation, as
in ``factory.post('/users/', data=body, content_type='application/xml')``. You
can also set the header explicitly with
``headers={'Content-Type': 'application/xml'}``.

Checking responses
~~~~~~~~~~~~~~~~~~

Responses are regular Django :class:`django.http.HttpResponse` instances.
Check their status, headers, and decoded body using the standard Django API, as
the test client example does.

``response.json()`` requires the response ``Content-Type`` to be
``application/json``. Inspect ``response.content`` directly for other formats.

Once you have the decoded value, choose an assertion that captures its complete
stable contract without hard-coding runtime-generated data. The
:doc:`test assertions guide <assertions>` explains how to use
``inline-snapshot`` and ``dirty-equals`` for both cases.

.. _pytest-django: https://pytest-django.readthedocs.io/
