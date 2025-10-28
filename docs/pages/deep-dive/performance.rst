Performance and Benchmarks
==========================

Results
-------

Sync
~~~~

.. figure:: /_static/images/benchmarks/sync.png
   :width: 700
   :align: center

Why so fast?

- We utilize :func:`msgspec.json.decode` and :func:`msgspec.json.encode`
  to parse json, it is the fastest json parsing tool in Python land
- We can support :class:`msgspec.Struct` models, which are faster than pydantic
- We provide :func:`django.urls.path` drop-in :doc:`../routing` replacement
  which is `x51 times <https://habr.com/ru/companies/tochka/articles/822431/>`_
  as fast as the default one
- We validate data smartly: we prepare models for validation in advance,
  so no runtime magic ever happens
- We have special :ref:`"production mode" <response_validation>`
  with fewer checks, so we can have the best of two worlds:
  strict development workflow and fast runtime for real users

Async
~~~~~

.. figure:: /_static/images/benchmarks/async.png
   :width: 700
   :align: center

While ``fastapi`` is faster at the moment, we have several ideas
to optimize ``django_modern_rest`` even further,
so it can be on par (or even faster!)
with the fastest python web frameworks in existence.

While keeping 100% of compatibility with the older libs and tools.


Technical details
-----------------

See source code for our
`benchmark suite <https://github.com/wemake-services/django-modern-rest/tree/master/benchmark>`_.

.. include:: ../../../benchmarks/README.md
   :parser: myst_parser.sphinx_
