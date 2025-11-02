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


Technical details
-----------------

See source code for our
`benchmark suite <https://github.com/wemake-services/django-modern-rest/tree/master/benchmarks>`_.

.. include:: ../../../benchmarks/README.md
   :parser: myst_parser.sphinx_
