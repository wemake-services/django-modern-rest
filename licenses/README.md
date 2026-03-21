# Vendored libraries

We vendor several libraries.
All licenses are always included with the source code and with the releases.

Libs:

- Swagger UI, Apache-2.0
- Redoc, MIT
- Scalar, MIT

Here are their versions:

- Swagger: 5.32.1
- Redoc: 2.5.2
- Scalar: 1.49.2

## To update

1. Update versions here
2. Update versions in `tests/test_integration/test_openapi/conftest.py`
   for CDN tests
3. Manually validate that everything works
