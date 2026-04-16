Describing response headers and cookies
=======================================


Describing headers
------------------

You also must specify which headers are returned (if any).

When using "real endpoints", you can provide ``headers`` parameter
to :class:`~dmr.metadata.ResponseSpec`
if there are headers you want to describe.
:class:`~dmr.headers.HeaderSpec` is here to help.
You can create both ``required=True``
(always must be present on the response object)
and ``required=False`` headers (might be missing in some cases):

.. literalinclude:: /examples/using_controller/validate_headers.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 29-32

.. note::

  All headers from the response objects are checked. We will report:

  - Required headers that exist in the spec, but not on the ``response``
  - Any headers that exist on the ``response``, but not present in the spec

  ``Content-Type`` header is the only one that is always added automatically.

With "raw endpoints" you can also use
:class:`~dmr.headers.NewHeader` marker which can set headers
with known values to the final response.

.. literalinclude:: /examples/using_controller/modify_headers.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 20

If you need headers with not static, but dynamic values, use "real endpoints"
and pass ``headers`` dict to
:meth:`~dmr.controller.Controller.to_response` method.

The last important thing about headers
is :attr:`~dmr.headers.HeaderSpec.skip_validation` attribute.
It is used to describe headers that:

1. Will be set in the response by someone else outside the framework,
   like HTTP proxy or Django's own middleware.
   See :class:`django.contrib.sessions.middleware.SessionMiddleware`
   as a notable example
2. Will be validated to be **NOT** present in the response from our framework.
   Since it is designed to be added later, it should not be already present

.. important::

  Header definitions are case insensitive according to the HTTP spec.
  ``Session`` and ``session`` is the same header.


Describing cookies
------------------

.. warning::

  Some may say that returning cookies is not "RESTful",
  because cookies is an implicit state, that RESTful APIs must not have.
  Be careful, only use this feature when you need to.

  See: https://parottasalna.hashnode.dev/is-it-okay-to-add-cookie-to-a-rest-api

We also support setting and validating response cookies.

You can use :class:`~dmr.cookies.NewCookie`
to add new cookies with statically known values to "raw endpoints".
Or :class:`~dmr.cookies.CookieSpec` with both types
of endpoints to describe response cookies.

.. literalinclude:: /examples/using_controller/modify_cookies.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 16

And you can set any cookies to :attr:`django.http.HttpResponse.cookies`
with "real endpoints". Since we have strict schemas,
it is required to describe the set cookies with
:class:`~dmr.cookies.CookieSpec`:

.. literalinclude:: /examples/using_controller/validate_cookies.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 23-24

The last important thing about cookies
is :attr:`~dmr.cookies.CookieSpec.skip_validation` attribute.
It is used to describe cookies that:

1. Will be set in the response by someone else outside the framework,
   like HTTP proxy or Django's own middleware.
   See :class:`django.contrib.sessions.middleware.SessionMiddleware`
   as a notable example
2. Will be validated to be **NOT** present in the response from our framework.
   Since it is designed to be added later, it should not be already present

.. note::

  All cookie parts are validated by default. Except ``expires`` field,
  because it is relative to the current time.

.. important::

  Cookie definitions are case sensitive according to the HTTP spec.
  ``Session`` and ``session`` are two different cookies.
