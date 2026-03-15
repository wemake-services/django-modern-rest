Installation
============

Modern REST requires the following:

- Python 3.11+
- Django 5.2+

.. attention::

  We **recommend** using the latest patch release of each Python and Django
  series, as only these versions are officially supported.

Install the package with your preferred tool:

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

The following packages are optional:

- ``'django-modern-rest[pydantic]'`` — `pydantic <https://github.com/pydantic/pydantic>`_
  for request and response models
- ``'django-modern-rest[msgspec]'`` — `msgspec <https://github.com/jcrist/msgspec>`_
  for models and the `fastest <https://jcristharif.com/msgspec/benchmarks.html>`_ JSON parsing
- ``'django-modern-rest[jwt]'`` — `PyJWT <https://pyjwt.readthedocs.io>`_ for :doc:`JWT auth <../auth/jwt>`
- ``'django-modern-rest[openapi]'`` — :doc:`OpenAPI schema <../openapi/openapi>` validation and better examples

We also recommend installing `django-stubs <https://github.com/typeddjango/django-stubs>`_
for typing Django itself

.. tip::

  You can combine extras, for example: ``django-modern-rest[pydantic,msgspec]``.

.. important::

  We highly recommend to always install
  `msgspec <https://github.com/jcrist/msgspec>`_, even when using just
  `pydantic <https://github.com/pydantic/pydantic>`_ for APIs,
  because we use ``msgspec`` to parse ``json``, when it is available,
  since it is `the fastest <https://jcristharif.com/msgspec/benchmarks.html>`_
  library out there for this task.

You do **not** need to add ``'dmr'`` to your ``INSTALLED_APPS``
unless you want to serve static files for the OpenAPI UI.

If you use the OpenAPI schema UI (e.g. Swagger), add ``'dmr'``
to ``INSTALLED_APPS`` in your ``settings.py``:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        'dmr',
    ]
