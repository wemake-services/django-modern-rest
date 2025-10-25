Integrations
============

Serializing QuerySets into models
---------------------------------

Django is built around its :class:`django.db.models.QuerySet` type.
Of course, we have to make sure that it is supported.

Let's say you have these models that you already work with:

.. literalinclude:: ../../django_test_app/server/apps/models_example/models.py
  :caption: models.py
  :linenos:

And you want to create an API that will work with your models.
To do that the first thing you need to do is to create
your API serializers / deserializers.

While it may seems that this is a duplication of code, and that it
should be possible to build serialization schemas out of Django models,
but that's quite rare in real apps. Because models and serialization
schemes must change independenly. Otherwise, your API would be a mess 100%.

.. literalinclude:: ../../django_test_app/server/apps/models_example/serializers.py
  :caption: serializers.py
  :linenos:

If you don't like how ``tag_list`` looks, you can do the same manually:

.. code:: python

   def post(self) -> UserSchema:
       user = user_create_service(self.parsed_body)
       return UserSchema.model_validate({
           'email': user.email,
           'role': user.role,
           'tags': user.tags.all(),
       })

While specifing ``model_config = pydantic.ConfigDict(from_attributes=True)``
on ``TagSchema`` and ``RoleSchema``.
Both options work, just choose what style do you like more.

Here's how the final :class:`~django_modern_rest.controller.Controller`
would look like:

.. literalinclude:: ../../django_test_app/server/apps/models_example/views.py
  :caption: views.py
  :linenos:

Now you have your REST API that returns fully typed model responses
and can work with :class:`~django.db.models.QuerySet`
and :class:`~django.db.models.Model` instances.


Bring your own DI
-----------------

We don't have any opinions about any DI that you can potentially use.
Because ``django-modern-rest`` is compatible with any of the existing ones.

You any DI that you already use with ``django``.

Try any of these officially recommended tools:

- https://github.com/reagento/dishka
- https://github.com/bobthemighty/punq

Or keep using what you already have :)


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
