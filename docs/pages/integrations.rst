Integrations
============


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

We don't ship our own pagination.
We (as our main design goal suggests) provide support
for any existing pagination plugin for Django.
Including the built-in :class:`django.core.paginator.Paginator`.

To do so, we only provide metadata for the default pagination:

.. literalinclude:: /examples/integrations/pagination.py
  :caption: views.py
  :language: python
  :linenos:

If you are using a different pagination system, you can define
your own metadata / models and use them with our framework.

.. autoclass:: dmr.pagination.Paginated
  :members:

.. autoclass:: dmr.pagination.Page
  :members:


django-filters
--------------

No special integration with
`django-filter <https://github.com/carltongibson/django-filter>`_
is required.

Everything just works.

.. code-block:: python

  import django_filters
  import pydantic
  from dmr import Controller, Query
  from dmr.plugins.pydantic import PydanticSerializer

  from your_app.models import User

  class UserFilter(django_filters.FilterSet):
      class Meta:
          model = User
          fields = ('is_active',)

  # Create query model for better docs:
  class QueryModel(pydantic.BaseModel):
      is_active: bool

  class UserModel(pydantic.BaseModel):
      username: str
      email: str
      is_active: bool

  class UserListController(
      Controller[PydanticSerializer],
      Query[QueryModel],
  ):
      def get(self) -> list[UserModel]:
          # Still pass `.GET` for API compatibility:
          user_filter = UserFilter(
               self.request.GET,
               queryset=User.objects.all(),
          )
          return [
              UserModel.model_validate(user, from_attributes=True)
              for user in user_filter.qs
          ]


CORS Headers
------------

No special integration with
`django-cors-headers <https://github.com/adamchainz/django-cors-headers>`_
is required.

Everything just works.


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
