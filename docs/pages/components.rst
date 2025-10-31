Components
==========

``django-modern-rest`` utilizes component approach to parse all
the unstructured things like headers, body, and cookies
into a string typed and validated model.

To use a component, you can just add it as a base class to your
:class:`~django_modern_rest.controller.Controller`
or :class:`~django_modern_rest.controller.Blueprint`.

How does it work?

- When controller / blueprint is first created,
  we iterate over all existing components in this class
- Next, we create a request parsing model during the import time,
  with all combined fields to be parsed later
- In runtime, when request is received, we provide the needed data
  for this single parsing model
- If everything is ok, we call the needed endpoint with the correct data
- If there's a parsing error we raise
  :exc:`~django_modern_rest.exceptions.RequestSerializationError`
  and return a beautiful error message for the user

You can use existing ones or create our own.


Existing components
-------------------

Parsing headers
~~~~~~~~~~~~~~~

.. autoclass:: django_modern_rest.components.Headers

Parsing query string
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: django_modern_rest.components.Query

Parsing request body
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: django_modern_rest.components.Body

Parsing path parameters
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: django_modern_rest.components.Path

Parsing cookies
~~~~~~~~~~~~~~~

.. autoclass:: django_modern_rest.components.Cookies


Base API
--------

.. autoclass:: django_modern_rest.components.ComponentParser
   :members:
