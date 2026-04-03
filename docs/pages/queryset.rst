Serializing models and Querysets
================================

.. rubric:: Quote of the day

.. epigraph::

   | There are things that are easy.
   | There are things that seem easy.
   | Usually they are different things.

   -- `Nikita Sobolev <https://github.com/sobolevn>`_, CPython core developer

Django is built around its :class:`~django.db.models.query.QuerySet` type.
Of course, we have to make sure that it is supported.

Prepare yourself for a wild ride!
This section will not only be about queryset,
but also about architecture of Django applications.

.. important::

  We offer a brand new way of working with
  :class:`~django.db.models.query.QuerySet`.

  It is the best thing that ever happened to Django's serialization.

  We built our serialization patterns on:

  1. Simplicity
  2. Database table independence from the serialization schema
  3. Customizability: you can change anything at anytime
  4. Performance: no extra fields, no extra queries, fast serialization
  5. Everything must be typed at all times


Oversimplied example
--------------------

Let's start with the very simple definition of a regular model,
with no foreign keys or many-to-many fields.

Our approach is to always move all the business logic away from the view.
Even in examples, because they form the habit
of developers and LLMs who are reading it.

.. seealso::

  Full-featured example with the proper layers can be found here:

  https://github.com/wemake-services/wemake-django-template/blob/master/%7B%7Bcookiecutter.project_name%7D%7D/server/apps/main/api/views.py

Model
~~~~~

Our regular :class:`~django.db.models.Model` definition:

.. literalinclude:: ../../django_test_app/server/apps/model_simple/models.py
  :caption: models.py
  :language: python
  :linenos:

For this example, the model won't have any FK or M2M fields.
In the next examples we will show how to work with them as well.

Serializer schemas
~~~~~~~~~~~~~~~~~~

Next, let's define serializer schemas
to get the incoming data and return the response.

You can use any schema type, including :class:`pydantic.BaseModel`,
:func:`attrs.define`, :class:`typing.TypedDict`, etc.
For this example we will use ``pydantic``, because
it is the most familiar tools for the most programmers:

.. literalinclude:: ../../django_test_app/server/apps/model_simple/serializers.py
  :caption: serializers.py
  :language: python
  :linenos:

.. important::

  This step is really important! Because we **have to** separate database
  models and serializer schemas from each other. Why?

  1. Because it gives us more control over the serialization process both ways
  2. Because new database fields will not automatically appear in your API spec
  3. Because removing a database field will not break the API contract
  4. Because versioning the API becomes much easier
  5. Because explicit typing will let you catch more errors earlier

Services
~~~~~~~~

Now, let's define our business logic.

.. note::

  We don't give any architectural advice here, you can use any approach
  that you like for your projects: DDD, Clean or Hexagonal Architecture,
  Functional Core and Imperative Shell, whatever you like.

  But, you business logic must be separated from views
  for better testing and better composition.

For this example, we will use the simplest ``services.py``
layer for our business logic:

.. literalinclude:: ../../django_test_app/server/apps/model_simple/services.py
  :caption: services.py
  :language: python
  :linenos:

There's nothing fancy about it. Just creating a model from the typed input data.

Views
~~~~~

Now, we can define views that will use everything from the above.

.. tabs::

  .. tab:: Minimalistic

    Just convert models from attributes,
    using the builtin  ``.model_validate()`` converter.
    For ``msgspec`` one can use :func:`msgspec.convert`.

    - The main reason to use this approach is that it is short and easy
    - The main reason not to use this approach is that errors will only show up
      during tests. Not during type-checking. For example,
      removing ``customer_service_uid`` from ``models.py``
      (for some business reason)
      will not trigger any type checking errors.
      If this line is not covered with tests, your API will not work:

      .. code-block::

        Traceback (most recent call last):
          File "server/apps/model_simple/views/minimalistic.py", line 42
            return UserSchema.model_validate(
            ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
        pydantic.ValidationError: Object missing required field `customer_service_uid`

    .. literalinclude:: ../../django_test_app/server/apps/model_simple/views/minimalistic.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: Detailed

    Convert models to schemas manually. It might seem like a lot of code,
    but actually, it is pretty simple to do with
    (especially with the help of LLM).

    - The main reason to use this approach is correctness.
      For example, removing ``customer_service_uid`` model field
      will now trigger an early type-checking error,
      unlike the "Minimalistic" version, which will only fail in runtime:

      .. code-block::

        server/apps/model_simple/views/detailed.py:28: error: "User" has no attribute "customer_service_uid"  [attr-defined]
        server/apps/model_simple/views/detailed.py:48: error: "User" has no attribute "customer_service_uid"  [attr-defined]

    - The main reason not to use this approach is its verbosity

    .. literalinclude:: ../../django_test_app/server/apps/model_simple/views/detailed.py
      :caption: views.py
      :language: python
      :linenos:

Now you have your REST API that returns fully typed model responses
and can work with :class:`~django.db.models.query.QuerySet`
and :class:`~django.db.models.Model` instances.


Realistic example
-----------------

Now, let's see how a more realistic layout may look like. It will include:

- ``ForeignKey`` relationship
- ``ManyToMany`` relationship
- DI for realistic expectations
- Mappers and services separate layers

Models
~~~~~~

We start with models definitions.

.. literalinclude:: ../../django_test_app/server/apps/model_fk/models.py
  :caption: models.py
  :language: python
  :linenos:

We added two models:

- ``Role`` for foreign key relation
- ``Tag`` for many-to-many relation

Serializer schemas
~~~~~~~~~~~~~~~~~~

Next, let's see how serializer schemas are defined.

.. literalinclude:: ../../django_test_app/server/apps/model_fk/serializers.py
  :caption: serializers.py
  :language: python
  :linenos:

Note that we model foreign key and many-to-many relations
here as nested schemas or list of nested schemas.
However, you can also model the same thing
as ``role_id: int`` and ``tags: list[int]`` to support ids for linking.
That's the beautify of this extremely simple approach:
it is customizable to the core.

Views
~~~~~

In this example, it would be easier to start with ``views.py``:

.. literalinclude:: ../../django_test_app/server/apps/model_fk/views.py
  :caption: views.py
  :language: python
  :linenos:

What happens here?

1. We refactored our views to only run an instance of a specific service,
   which we get using ``HasContainer.resolve`` call, which is our DI
2. We now don't construct any serializer schemas inside our views,
   we move to its independent infra layer
3. We now use :ref:`pagination` to list all users

Our views here are reduced to a single line of code, which do everything
inside the business logic. Exactly the way it should
be for scalable and reliable applications.

DI
~~

In this example we use `punq <https://github.com/bobthemighty/punq>`_
as a simplistic DI container to show how big projects really handle such cases.

.. note::

  You are not forced to use ``punq``, we don't enforce any DI framework.
  Our principle is to :ref:`bring-your-own-di`.

The DI part looks like this:

.. literalinclude:: ../../django_test_app/server/apps/model_fk/implemented.py
  :caption: views.py
  :language: python
  :linenos:

What happens here?

1. We define a class that will be used as a mixin for all future controllers
2. This class provides a pre-built container with all the dependencies
3. Users can call ``self.resolve`` inside controllers
   to resolve specific dependencies

Now, let's see how we create objects in the database.

Services
~~~~~~~~

Again, this is just an example. You are not forced
to create this specific service-based architecture.
Use whatever layers separation practice as you want.
Our big example uses `usecases <https://github.com/wemake-services/wemake-django-template/tree/master/%7B%7Bcookiecutter.project_name%7D%7D/server/apps/main/logic/usecases>`_
as the main logic entities and entry points.

However, our ``services.py`` is the simplest and the shortest way.
That's why we are using them as an example:

.. literalinclude:: ../../django_test_app/server/apps/model_fk/services.py
  :caption: services.py
  :language: python
  :linenos:

What happens here?

1. We define three services: one per create operation
2. Some of them have dependencies defined as dataclass fields,
   like ``_mapper: UserMap``, these fields will be resolved by our DI
3. Each service does just a single thing, it would be easy to compose them

Now we are ready for the final layer: mapping of the created database models.

Mappers
~~~~~~~

Mappers just map database models into serialization schemas.

.. tip::

  In real projects, it is better to have a separate layer that does mapping
  of database models into
  `serialization schemas <https://github.com/wemake-services/wemake-django-template/blob/master/{{cookiecutter.project_name}}/server/apps/main/infra/mappers.py>`_

  It will allow you to compose mappers freely.
  For example, it allows you to create compatibility layers,
  when some model have some database fields removed,
  but still need a way to send users the same API schema.

  Or it can do some small representation logic, like combining
  ``first_name`` and ``last_name`` of users into ``full_name``.

  Or handle :ref:`pagination`, as we do in this example.

.. literalinclude:: ../../django_test_app/server/apps/model_fk/mappers.py
  :caption: mappers.py
  :language: python
  :linenos:

Now we have a fully working application.
With composable and flexible schemas, which will:

1. Report any type errors early
2. Be customizable to the core
3. Can be used in a good architecture in big real business apps
4. Change independently from models


Conclusions
~~~~~~~~~~~

Here's the final table to help you decide what to use:

+------------------+----------------------+
| Your App         | What to Use          |
+==================+======================+
| Todo App         | Minimalistic Example |
+------------------+----------------------+
| Real Application | Mappers              |
+------------------+----------------------+


django-mantle
-------------

If you want to automate the mapping part and automagically
convert ``QuerySet`` into typed models, you can use
`django-mantle <https://noumenal.es/mantle/>`_.

- Allows you to move your business logic into type-safe Python classes,
  decoupled from the Django ORM.
- Provides automatic generation (with declarative overrides)
  of efficient ORM queries, including limited field fetches
  with ``only()`` and ``defer()`` and prefetching related objects,
  avoiding N+1 query problems.
- Uses a modern and performant approach to serialisation and validation.
- Provides a progressive API, with a minimal surface
  area by default, and depth when needed.

It’s your type-safe layer around Django’s liquid core.

.. literalinclude:: /examples/queryset/django_mantle.py
  :caption: views.py
  :language: python
  :linenos:
