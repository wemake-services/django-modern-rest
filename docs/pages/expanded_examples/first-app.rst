First app
=============================

In this tutorial we step-by-step create single-file application with simple CRUD.
If you don't understand any of the concepts, please read our :doc:`Core concepts </pages/core-concepts>`

Preparing
---------

First of all, create a project folder and create a virtual environment (we strongly recommend it).

Add django-modern-rest:

.. tabs::

    .. tab:: :iconify:`material-icon-theme:uv` uv

        .. code-block:: bash

            uv add django-modern-rest

    .. tab:: :iconify:`devicon:poetry` poetry

        .. code-block:: bash

            poetry add django-modern-rest

    .. tab:: :iconify:`devicon:pypi` pip

        .. code-block:: bash

            pip install django-modern-rest

Hello world
-----------

In this section we create app that have only one greeting :term:`Endpoint`.
In simple words an `Endpoint` is address to function that the server must execute.

Lets create our `main.py` file with the following code.

.. literalinclude:: /examples/expanded/first_app_00_hello.py
   :language: python
   :linenos:

Now lets run our app using the following command:

.. code-block:: bash

   python main.py runserver

When all goes fine you will see something like this:

.. code-block::

   Watching for file changes with StatReloader
   Performing system checks...

   System check identified no issues (0 silenced).
   March 04, 2026 - 13:26:37
   Django version 6.0.2, using settings None
   Starting development server at http://127.0.0.1:8000/
   Quit the server with CONTROL-C.

   WARNING: This is a development server. Do not use it in a production setting. Use a production WSGI or ASGI server instead.
   For more information on production servers see: https://docs.djangoproject.com/en/6.0/howto/deployment/


Then go to you browser and visit http://localhost:8000/.
You will see `"Hello from Django Modern Rest!"` message.

Congrats! You've run your first app with `dmr`.
But its looks to simple and we even don't import `dmr` itself, right?

Lets expand our code.

Meangfull endpoints
-------------------

Honestly our previous example do nothing useful.

Lets expand our application and add 2 endpoints: one for set user and one for get all users.
Note that we use dict as database. It will not be saved between different app runs, but for our case, it's enough.

Let's change our previous code:

.. literalinclude:: /examples/expanded/first_app_01_meangfull.py
   :language: python
   :linenos:
   :emphasize-lines: 3,6, 8-11, 23-43, 51-52

Let's test our new endpoints.
You can go to http://localhost:8000/get_users and see content of database.

Test the `set_user` endpoint with following command:

.. code-block:: bash

  curl -X POST http://localhost:8000/set_user -H "Content-Type: application/json" -d '{"id": "3", "name": "John"}'

You will see this response in terminal:

.. code-block::

  {"status": "success", "data": {"1": "Alex", "2": "Sasha", "3": "John"}}

If you go to our get_users endpoint it shows you extended database with 3 people.

Its code seems good but has a big problem: its hard to scale it in real projects.


Routes, Controllers and Swagger
-------------------------------

.. note::

  In this section, we will use :doc:`Routing </pages/routing>` and :doc:`Controllers</pages/using-controller>`.
  We will provide a simple explanation of it. Feel free to read specific section of our documentation at any time!

First of all, lets combine our endpoints to route.

What is a route? In simple words route collects all provided URLs to single entry point.
Its useful to make your code more readable and expanded.

In our case let's split our endpoints to separate routes. Change whole url_patterns to this:

.. literalinclude:: /examples/expanded/first_app_02_routes.py
   :language: python
   :linenos:
   :emphasize-lines: 4, 8, 49-61, 67-71

Note that new endpoints will change to http://localhost:8000/api/get_users and http://localhost:8000/api/set_user

But what's next? Next we add :term:`Controller` to our app

What is controller? A Controller is a class that handle all endpoints with the same set of components of our system.
This means that if we have set of endpoints to interact with user (create, modify, delete) its better to put them in a single UserController.
Also controller can help to verify your data easily.

In our case, we'll create 2 controllers (one for user and another for users).
Notice, that we remove our previous functions get_users and set_user and move logic to controllers with modification

.. literalinclude:: /examples/expanded/first_app_03_controller.py
   :language: python
   :linenos:
   :emphasize-lines: 7-10, 27-85


Now all data will be validate and app can be scaled!


Swagger
-------

Last thing that we will do in this simple example is connect Swagger docs to our app.
It will help you to debug all of your endpoints.

For this, lets add the following code:

.. literalinclude:: /examples/expanded/first_app_04_swagger.py
   :language: python
   :linenos:
   :emphasize-lines: 12-13, 29-48, 106-133


And then visit https://localhost:8000/docs/swagger for the interactive docs.

.. image:: /_static/images/swagger.png
   :alt: Swagger view
   :align: center

Note that new endpoints will change to http://localhost:8000/api/users/get_users and http://localhost:8000/api/user/set_user

That's it! Enjoy your new project!
