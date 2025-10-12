# django-modern-rest

[![test](https://github.com/wemake-services/django-modern-rest/actions/workflows/test.yml/badge.svg?event=push)](https://github.com/wemake-services/django-modern-rest/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/wemake-services/django-modern-rest/branch/master/graph/badge.svg)](https://codecov.io/gh/wemake-services/django-modern-rest)
[![Python Version](https://img.shields.io/pypi/pyversions/django-modern-rest.svg)](https://pypi.org/project/django-modern-rest/)
[![wemake-python-styleguide](https://img.shields.io/badge/style-wemake-000000.svg)](https://github.com/wemake-services/wemake-python-styleguide)

Modern REST framework for Django with types and async support!


## Features

- [x] Blazingly fast
- [x] Fully typed and checked with `mypy` and `pyright`
- [x] Supports `pydantic2`, but not bound to it. 
- [ ] Supports `msgspec` support
- [x] Supports async Django
- [ ] Supports `openapi` schema generation out of the box
- [x] Supports all your existing `django` primitives and packages
- [x] Does not use `from __future__ import annotations`
- [ ] 100% test coverage
- [x] No emojis 🌚️️


## Installation

```bash
pip install django-modern-rest
```

There are several included extras:
- `'django-modern-rest[pydantic]'` provides `pydantic` support


## Example

TODO: ...


## License

[MIT](https://github.com/wemake-services/django-modern-rest/blob/master/LICENSE)


## Credits

This project was generated with [`wemake-python-package`](https://github.com/wemake-services/wemake-python-package). Current template version is: [e1fcf312d7f715323dcff0d376a40b7e3b47f9b7](https://github.com/wemake-services/wemake-python-package/tree/e1fcf312d7f715323dcff0d376a40b7e3b47f9b7). See what is [updated](https://github.com/wemake-services/wemake-python-package/compare/e1fcf312d7f715323dcff0d376a40b7e3b47f9b7...master) since then.
