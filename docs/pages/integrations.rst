Integrations
============

Big list of Django integrations: https://github.com/wsvincent/awesome-django

.. warning::

  In the future - some integrations from this list might be included
  into the core of ``django-modern-rest`` package. Or ship as plugins.

  If you are interested in something:
  `open an issue <https://github.com/wemake-services/django-modern-rest/issues>`_.


CSRF
----

Django supports
`Cross Site Request Forgery <https://docs.djangoproject.com/en/stable/ref/csrf/>`_
protection.

By default we exempt all controllers from CSRF checks, unless:

1. :attr:`~dmr.controller.Controller.csrf_exempt`
   is set to ``False`` for a specific controller
2. Endpoints protected by
   :class:`~dmr.security.django_session.auth.DjangoSessionSyncAuth`
   or
   :class:`~dmr.security.django_session.auth.DjangoSessionAsyncAuth`
   will require CSRF as well. Because using Django sessions
   without CSRF is not secure


.. _bring-your-own-di:

Bring your own DI
-----------------

We don't have any opinions about any DI that you can potentially use.
Because ``django-modern-rest`` is compatible with any of the existing ones.

Use any DI that you already have or want to use with ``django``.

Try any of these officially recommended tools:

- https://github.com/maksimzayats/diwire
  with the official
  `django-modern-rest how-to <https://docs.diwire.dev/howto/web/django-modern-rest.html>`_
- https://github.com/reagento/dishka with the help of https://github.com/arturboyun/dmr-dishka plugin
- https://github.com/bobthemighty/punq

Or any other one that suits your needs :)


Typing
------

Django does not have type annotations, by default,
so ``mypy`` won't type check Django apps by default.
But, when `django-stubs <https://github.com/typeddjango/django-stubs>`_
is installed, type checking starts to shine.

So, when you use ``mypy``, you will need
to install ``django-stubs`` together with ``django-modern-rest``
to have the best type checking experience.

This package is included in ``pyright`` by default. No actions are required.

We check ``django-modern-rest`` code with ``mypy`` and ``pyright``
strict modes in CI, so be sure to have the best typing possible.

See our
`project template <https://github.com/wemake-services/wemake-django-template>`_
to learn how typing works, how ``mypy`` is configured,
how ``django-stubs`` is used.


.. _pagination:

Pagination
----------

Limit Offset pagination
~~~~~~~~~~~~~~~~~~~~~~~

We support built-in :class:`django.core.paginator.Paginator`.

To do so, we only provide metadata for the default pagination:

.. literalinclude:: /examples/integrations/pagination.py
  :caption: views.py
  :language: python
  :linenos:

If you are using a different pagination system, you can define
your own metadata / models and use them with our framework.

Cursor pagination
~~~~~~~~~~~~~~~~~

We also support any other pagination library.

Like `django-cursor-pagination <https://github.com/photocrowd/django-cursor-pagination>`_
or even your custom implementation.

Any Django-compatible tool should work out of the box.

Interface
~~~~~~~~~

.. autoclass:: dmr.pagination.Paginated
  :members:

.. autoclass:: dmr.pagination.Page
  :members:


Filters
-------

No special integration with
`django-filter <https://github.com/carltongibson/django-filter>`_
is required.

Everything just works:

.. literalinclude:: /examples/integrations/filters.py
  :caption: views.py
  :language: python
  :linenos:


Health Checks
-------------

We recommend using
`django-health-check <https://github.com/codingjoe/django-health-check>`_
for monitoring your application's health.

No special integration is required — the package works out-of-the-box with
``django-modern-rest``. Simply install it, include its URLs in your main
urlconf, and add the desired check apps to ``INSTALLED_APPS``.

For advanced configuration, please refer to the
`django-health-check documentation <https://codingjoe.dev/django-health-check>`_.


CORS Headers
------------

No special integration with
`django-cors-headers <https://github.com/adamchainz/django-cors-headers>`_
is required.

Everything just works.


.. _content_security_policy:

Content Security Policy (CSP)
-----------------------------

No special integration with
`django-csp <https://github.com/mozilla/django-csp>`_
is required.

Everything just works, but there is one important nuance:
``django-modern-rest`` itself only controls Django templates and local
initialization files. If you use OpenAPI UI renderers, final CSP compatibility
still depends on the upstream frontend bundle you choose.

The OpenAPI UI templates shipped by ``django-modern-rest`` avoid inline
``<script>`` blocks and pass schema data via Django's
:func:`django.utils.html.json_script`, so DMR's own templates work well with
stricter CSP setups.

Known caveats:

- Some upstream OpenAPI bundles inject styles at runtime, so a very strict
  policy can still break the page.
- When CSP is a hard requirement, start with local bundled assets and test
  the exact renderer and version you plan to deploy.

Example ``django-csp`` setup can be found in
`wemake-django-template <https://github.com/wemake-services/wemake-django-template/blob/master/%7B%7Bcookiecutter.project_name%7D%7D/server/settings/components/csp.py>`_.

If you use OpenAPI UIs, see :doc:`openapi/openapi`
for renderer-specific guidance.


Conditional requests (ETag)
---------------------------

Django has built-in support for conditional request processing
(``If-None-Match``, ``If-Modified-Since``, ``304 Not Modified``):

With ``django-modern-rest`` you can integrate it via
:func:`~dmr.decorators.wrap_middleware`
and :func:`django.views.decorators.http.condition`.


.. literalinclude:: ../../django_test_app/server/apps/etag/views.py
  :caption: etag.py
  :language: python
  :linenos:

.. seealso::

    https://docs.djangoproject.com/en/stable/topics/conditional-view-processing


HTMX
----

Works with `django-htmx <https://github.com/adamchainz/django-htmx>`_
out of the box.
