Performance and Benchmarks
==========================

Results
-------

Sync
~~~~

.. chartjs::

  {
    "type": "bar",
    "data": {
      "labels": ["Requests Per Second"],
      "datasets": [
        {
          "label": "dmr",
          "data": [5774.94],
          "backgroundColor": ["rgba(37, 108, 86, 0.7)"],
          "borderColor": ["rgba(53, 84, 74, 1)"],
          "borderWidth": 2
        },
        {
          "label": "ninja",
          "data": [3888.13],
          "backgroundColor": ["rgba(53, 84, 74, 0.4)"],
          "borderColor": ["rgba(53, 84, 74, 0.7)"],
          "borderWidth": 2
        },
        {
          "label": "drf",
          "data": [3024.24],
          "backgroundColor": ["rgba(53, 84, 74, 0.3)"],
          "borderColor": ["rgba(53, 84, 74, 0.6)"],
          "borderWidth": 2
        }
      ]
    },
    "options": {
      "responsive": true,
      "maintainAspectRatio": true,
      "scales": {
        "y": {
          "beginAtZero": true,
          "title": {
            "display": true,
            "text": "higher is better"
          }
        },
        "x": {
          "grid": {
            "display": false
          }
        }
      },
      "plugins": {
        "legend": {
          "display": true,
          "position": "top",
          "labels": {
            "usePointStyle": true
          }
        }
      }
    }
  }

Why so fast?

- We utilize :func:`msgspec.json.decode` and :func:`msgspec.json.encode`
  to parse json, it is the fastest json parsing tool in Python land
- We can support :class:`msgspec.Struct` models, which are faster than pydantic
- We :ref:`compile <mypyc>` some hot paths of the framework
  with `mypyc <https://mypyc.readthedocs.io/en/latest/>`_ to C code,
  while keeping fallback Python code in-place
- We provide :func:`django.urls.path` drop-in :doc:`../routing` replacement
  which is `x51 times <https://habr.com/ru/companies/tochka/articles/822431/>`_
  as fast as the default one
- We validate data smartly: we prepare models for validation in advance,
  so no runtime magic ever happens
- We have special :ref:`"production mode" <response_validation>`
  with fewer checks, so we can have the best of two worlds:
  strict development workflow and fast runtime for real users

We also support `PyPy <https://github.com/pypy/pypy>`_, which can be several
orders of magnitude faster that CPython.

Async
~~~~~

.. chartjs::

  {
    "type": "bar",
    "data": {
      "labels": ["Requests Per Second"],
      "datasets": [
          {
            "label": "fastapi",
            "data": [10854.6],
            "backgroundColor": ["rgba(53, 84, 74, 0.4)"],
            "borderColor": ["rgba(53, 84, 74, 0.7)"],
            "borderWidth": 2
          },
          {
            "label": "dmr",
            "data": [7026.27],
            "backgroundColor": ["rgba(37, 108, 86, 0.7)"],
            "borderColor": ["rgba(53, 84, 74, 1)"],
            "borderWidth": 2
          },
          {
            "label": "ninja",
            "data": [4359.12],
            "backgroundColor": ["rgba(53, 84, 74, 0.3)"],
            "borderColor": ["rgba(53, 84, 74, 0.6)"],
            "borderWidth": 2
          }
        ]
    },
    "options": {
      "responsive": true,
      "maintainAspectRatio": true,
      "scales": {
        "y": {
          "beginAtZero": true,
          "title": {
            "display": true,
            "text": "higher is better"
          }
        },
        "x": {
          "grid": {
            "display": false
          }
        }
      },
      "plugins": {
        "legend": {
          "display": true,
          "position": "top",
          "labels": {
            "usePointStyle": true
          }
        }
      }
    }
  }

While ``fastapi`` is faster at the moment, we have several ideas
to optimize ``django-modern-rest`` even further,
so it can be on par (or even faster!)
with the fastest python web frameworks in existence.

While keeping 100% of compatibility with the older libs and tools.


.. _mypyc:

mypyc compilation
-----------------

We compile several parts of the framework with ``mypyc``.
What does it mean?

1. We still write all code in good old pure Python
2. We add annotations to all code anyway
3. We then compile some modules from annotated Python to C with ``mypyc``
4. It starts to work from 4 to 10 times faster for free
5. We ship pre-built wheels with the built binaries for multiple platforms
6. For platforms with binary deps, it is possible to disable binary parts
   and switch to Python code with :envvar:`DMR_USE_COMPILED` set to ``0``,
   for example when you need to debug something
7. For unsupported platforms / ``sdist`` installs,
   we still ship pure Python code

What do we compile?

We only compile code that makes sense to be compiled.
Criteria:

1. Does not have IO
2. Does not have a lot of compiled / uncompiled context switches. For example,
   compiled code that frequently calls Python code
   will most like be slower in the result
3. Is executed on the hot path. Not in import time,
   but in request's handing phase
4. Is rather simple and does not have a lot of magic,
   otherwise - compilation will not have much effect
5. Does not have complex typing
6. Have no external dependencies
7. It shows a decent speedup in a micro-benchmark

Compiled features
~~~~~~~~~~~~~~~~~

- ``Accept`` header parsing and content negotiation

Supported platforms
~~~~~~~~~~~~~~~~~~~

Wheels are available for:

- Linux (via both the manylinux and musllinux standards)
- macOS (both x86_64 and aarch64)
- 64-bit versions of Windows (AMD only, ARM is not supported at the moment)

We support wheels for all supported Python versions.

``django-modern-rest`` is a pure Python project, so any "unsupported" platforms
will just fall back to the slower pure Python wheel available on PyPI.

If you want to force
`sdist <https://packaging.python.org/en/latest/glossary/#term-Source-Distribution-or-sdist>`_
build, pass ``--no-binary django-modern-rest``,
however this might only be useful in very strange cases.

Building your own wheels from source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ``make wheel`` to run the compilation.


Technical details
-----------------

See source code for our
`benchmark suite <https://github.com/wemake-services/django-modern-rest/tree/master/benchmarks>`_.

.. include:: ../../../benchmarks/README.md
   :parser: myst_parser.sphinx_
