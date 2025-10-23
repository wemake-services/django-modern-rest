django-modern-rest
==================

.. container:: badges
   :name: badges

   .. image:: https://github.com/wemake-services/django-modern-rest/actions/workflows/test.yml/badge.svg?event=push
      :alt: Tests result

   .. image:: https://codecov.io/gh/wemake-services/django-modern-rest/branch/master/graph/badge.svg
      :alt: Coverage

   .. image:: https://img.shields.io/pypi/pyversions/django-modern-rest.svg
      :alt: Supported Python versions

   .. image:: https://img.shields.io/badge/style-wemake-000000.svg
      :alt: Code style

   .. image:: https://img.shields.io/badge/%20-wemake.services-green.svg?label=%20&logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAABGdBTUEAALGPC%2FxhBQAAAAFzUkdCAK7OHOkAAAAbUExURQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP%2F%2F%2F5TvxDIAAAAIdFJOUwAjRA8xXANAL%2Bv0SAAAADNJREFUGNNjYCAIOJjRBdBFWMkVQeGzcHAwksJnAPPZGOGAASzPzAEHEGVsLExQwE7YswCb7AFZSF3bbAAAAABJRU5ErkJggg%3D%3D
      :alt: Developed by


.. rst-class:: lead

  Modern REST framework for Django with types and async support!

This guide will walk you through all the details of how to install, use,
and extend ``django-modern-rest`` framework.


.. container:: buttons

    :doc:`pages/getting-started`
    `GitHub <https://github.com/wemake-services/django-modern-rest>`_


Main features include:

.. grid:: 1 1 2 2
    :class-row: surface
    :padding: 0
    :gutter: 2

    .. grid-item-card:: :octicon:`terminal` REST
      :link: pages/core-concepts
      :link-type: doc

      Semantic REST APIs with 100% typed API and strict schema validation
      for both requests and responses.

      You would never miss an important status code in the docs anymore!

    .. grid-item-card:: :octicon:`zap` Blazingly Fast!
      :link: pages/performance
      :link-type: doc

      Built with performance in mind. Import time optimizations,
      only one validation per request, best ``json`` parsing tools in class.

      And ``msgspec`` support allows users to have
      `x5-15 times faster <https://jcristharif.com/msgspec/benchmarks.html>`_
      APIs than the alternatives.

    .. grid-item-card:: :octicon:`star` Sync and Async support
      :link: pages/core-concepts
      :link-type: doc

      Fully utilizes best of the both worlds in ``django``.

      Create your APIs as sync or async, your choice.
      Both ``wsgi`` and ``asgi`` are supported.

    .. grid-item-card:: :octicon:`beaker` Not just schema generation
      :link: pages/openapi
      :link-type: doc

      Of course, OpenAPI schema generation and modification
      are available out of the box.

      But, there's more: we also provide validation
      and testing tools for your schema!
      Powered by `schemathesis <https://github.com/schemathesis/schemathesis>`

    .. grid-item-card:: :octicon:`rocket` Still good old Django
      :link: pages/core-concepts
      :link-type: doc

      We don't reinvent the wheel, this is just good old Django.
      We only add fast ``json`` parsing and schema for requests and responses.

      And that's it. You can still use all packages
      and features from regular Django apps.
      No new concepts to learn, no new APIs to be compatible with.

      Just drop this package into any existing Django application!

    .. grid-item-card:: :octicon:`gear` Customizable to the core
      :link: pages/deep-dive/public-api
      :link-type: doc

      Every part of the framework can be customized and extended.

      Since, there's no magic happening, it would be really easy to do.
      Our docs and tests provide multiple examples of that.

      Public API stability is guaranteed.



Contributors
------------

Here are our amazing people who made this project possible.

.. container:: rounded-image

    .. contributors:: wemake-services/django-modern-rest
        :avatars:
        :contributions:


.. toctree::
  :caption: User Guide
  :hidden:

  pages/getting-started.rst
  pages/core-concepts.rst
  pages/configuration.rst
  pages/openapi.rst
  pages/bring-your-own-di.rst
  pages/performance.rst
  pages/testing.rst


.. toctree::
  :caption: Deep Dive
  :hidden:

  pages/deep-dive/public-api.rst
  pages/deep-dive/internal-api.rst
  pages/deep-dive/changelog.rst
