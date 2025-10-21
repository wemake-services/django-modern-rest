django-modern-rest
==================

.. rst-class:: lead
  Modern REST framework for Django with types and async support!

This guide will walk you through all the details of how to install, use,
and extend ``django-modern-rest`` framework.


Installations
-------------


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


Showcase
--------

Quick example:

.. tabs::

    .. tab:: msgspec

      .. literalinclude:: /examples/getting_started/msgspec_controller.py
        :linenos:
        :emphasize-lines: 6, 22

    .. tab:: pydantic

      .. literalinclude:: /examples/getting_started/pydantic_controller.py
        :linenos:
        :emphasize-lines: 6, 22


Contributors
------------

Here are our amazing people who made this project possible.

.. container:: rounded-image

    .. contributors:: wemake-services/django-modern-rest
        :avatars:
        :contributions:


.. toctree::
  :caption: Contents
  :hidden:

  pages/bring-your-own-di.rst
  pages/changelog.rst
