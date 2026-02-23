Integrations
============

Serializing QuerySets into models
---------------------------------

Django is built around its :class:`~django.db.models.query.QuerySet` type.
Of course, we have to make sure that it is supported.

Let's say you have these models that you already work with:

.. literalinclude:: ../../django_test_app/server/apps/models_example/models.py
  :caption: models.py
  :language: python
  :linenos:

Now, let's create an API that will work with your models.
To do that the first thing you need to do is to create
your API serializers / deserializers.

While it may seems that this is a redundant duplication of code, and that it
should be possible to build serialization schemas out of Django models,
but that's actually the **opposite**.

Because models and serialization
schemes must change independenly. Otherwise, your API would
be a mess and will change unexpectedly, when you create a new migration.
This problem happened to me too many times.

.. literalinclude:: ../../django_test_app/server/apps/models_example/serializers.py
  :caption: serializers.py
  :language: python
  :linenos:

.. important::

  Models and QuerySets can't be serialized to json by default.
  This is a design choice, this is a feature.

  Why?

  Because Models and QuerySets are not designed for serialization,
  they are designed for the database access. Mixing these two layers
  will **complicate**, not simplify, your app.

Now, let's create a service to build your model instances:

.. literalinclude:: ../../django_test_app/server/apps/models_example/services.py
  :caption: services.py
  :language: python
  :linenos:

Here's how the final :class:`~dmr.controller.Controller`
would look like:

.. literalinclude:: ../../django_test_app/server/apps/models_example/views.py
  :caption: views.py
  :language: python
  :linenos:

Now you have your REST API that returns fully typed model responses
and can work with :class:`~django.db.models.query.QuerySet`
and :class:`~django.db.models.Model` instances.


CSRF
----

Django supports
`Cross Site Request Forgery <https://docs.djangoproject.com/en/6.0/ref/csrf/>`_
protection.

By default we exempt all controllers from CSRF checks, unless:

1. :attr:`~dmr.controller.Controller.csrf_exempt`
   is set to ``False`` for a specific controller
2. Endpoints protected by
   :class:`~dmr.security.django_session.DjangoSessionSyncAuth`
   or
   :class:`~dmr.security.django_session.DjangoSessionAsyncAuth`
   will require CSRF as well. Because using Django sessions
   without CSRF is not secure


Bring your own DI
-----------------

We don't have any opinions about any DI that you can potentially use.
Because ``django-modern-rest`` is compatible with any of the existing ones.

Use any DI that you already have or want to use with ``django``.

Try any of these officially recommended tools:

- https://github.com/reagento/dishka
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

This package is included into ``pyright`` by default. No actions are required.

We check ``django-modern-rest`` code with ``mypy`` and ``pyright``
strict modes in CI, so be sure to have the best typing possible.

See our
`project template <https://github.com/wemake-services/wemake-django-template>`_
to learn how typing works, how ``mypy`` is configured,
how ``django-stubs`` is used.


Pagination
----------

We don't ship our own pagination.
We (as our main design goal suggests) provide support
for any existing pagination plugin for Django.
Including builtin :class:`django.core.paginator.Paginator`.

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
