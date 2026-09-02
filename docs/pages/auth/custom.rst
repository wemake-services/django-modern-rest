Writing your own auth
=====================

We ship auth for the transports most APIs need:
:doc:`http-basic`, :doc:`django-session`, :doc:`jwt`, :doc:`token`,
and :doc:`allauth`.

Sooner or later you will need one we don't ship: credentials that come
from a reverse proxy, a signed request, a hardware token, or a legacy
scheme some client of yours cannot stop sending. This page shows how to
write that auth yourself.

.. note::

  Before writing a new auth class, check whether you only need to change
  *where* the credentials come from. Most of our classes let you swap
  the header, the cookie, or the model without any new code.


The contract
------------

Your auth class subclasses :class:`~dmr.security.SyncAuth`
or :class:`~dmr.security.AsyncAuth` and implements several things:

.. list-table::
  :header-rows: 1
  :widths: 30 70

  * - Member
    - What it does
  * - :meth:`~dmr.security.SyncAuth.__call__`
    - Decides whether this request is authenticated.
  * - :meth:`~dmr.security.SyncAuth.security_schemes`
    - Describes the auth itself in the OpenAPI spec.
  * - :meth:`~dmr.security.SyncAuth.security_requirement`
    - References that description from every endpoint using this auth.

There is one more optional method:
:meth:`~dmr.metadata.ResponseSpecProvider.provide_response_specs`
declares extra responses your auth can produce.
We cover it :ref:`below <auth-extra-responses>`.


A worked example
----------------

Let's authenticate requests that come through a reverse proxy which has
already checked the user, and passes the username down in a header.
This is how ``oauth2-proxy`` and most SSO gateways work.

.. danger::

  Only ever do this when the proxy is guaranteed to **strip** that header
  from incoming client requests. Otherwise anyone can send
  ``X-Forwarded-User: admin`` and log in as anybody.

.. literalinclude:: /examples/auth/custom/auth.py
  :caption: auth.py
  :linenos:
  :language: python

Now use it like any auth we ship:

.. literalinclude:: /examples/auth/custom/views.py
  :caption: views.py
  :linenos:
  :language: python


Deciding the outcome
~~~~~~~~~~~~~~~~~~~~

:meth:`~dmr.security.SyncAuth.__call__` has four possible outcomes,
and picking the right one is the part that is easy to get wrong:

.. list-table::
  :header-rows: 1
  :widths: 35 65

  * - Outcome
    - What happens
  * - ``return self``
    - Authentication succeeded, we stop and run the endpoint.
  * - ``return None``
    - This auth does not apply, we try the next one in the chain.
      When it is the last one, the request gets a ``401``.
  * - raise :exc:`~dmr.exceptions.NotAuthenticatedError`
    - Authentication failed, we stop the chain right there
      and return a ``401``.
  * - raise :exc:`~dmr.response.APIError`
    - Same, but with a status code of your choice.
      Use it when the credentials are malformed rather than wrong.

The rule of thumb: return ``None`` while you still cannot tell whether
the client meant to use this auth at all, and raise once you can.

In the example above the header being absent means "not my request",
so we return ``None``. A header with an unknown username means
"my request, and it is wrong", so ``get_user`` raises.

.. warning::

  Getting this backwards breaks auth chains in a way that is easy to miss.
  We shipped that bug ourselves in :issue:`1289`: our cookie-based auth
  ran its CSRF check before looking at whether its cookie was even
  present, so a request carrying no cookie at all could never fall
  through to the next auth in the chain.

  If your auth does anything that can fail before it knows the request
  is meant for it, do that check *after* you have the credentials.


Describing it in OpenAPI
~~~~~~~~~~~~~~~~~~~~~~~~

The two ``security_*`` properties work together:

- ``security_schemes`` returns the named definitions to publish in
  ``components.securitySchemes``. A name maps to a
  :class:`~dmr.openapi.objects.SecurityScheme`
- ``security_requirement`` returns the names an endpoint requires,
  which lands in the operation's ``security`` field

Pick the ``type`` that matches your transport. Our example reads its own
header, so it is ``apiKey``. Had it read ``Authorization``, it would be
``type='http'`` with a ``scheme``, and OpenAPI clients would render
a proper login box for it.

Both are properties, not class attributes, because they usually depend
on the instance configuration, like the header name above.


Setting the request attributes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A successful auth is expected to tell the rest of the request who
the user is:

- ``request.user`` is what your endpoints and Django itself read
- ``request.auser`` is its awaitable counterpart. Set it even in sync
  auth, so code that crosses the sync / async boundary keeps working

Annotate the controller with
:class:`~dmr.security.AuthenticatedHttpRequest` once you set ``user``,
and ``self.request.user`` becomes properly typed, as in ``views.py``
above.

We also store the auth instance itself on the request, so
:func:`~dmr.security.request_auth` can tell you which auth of the chain
succeeded. That one we set for you, you don't have to.

If your auth resolves something else worth keeping, like a token row or
a session, store it under a name of your own and give your users
a helper to read it back. That is exactly what
:func:`~dmr.security.jwt.auth.request_jwt`
and :func:`~dmr.security.token.request_token` do.


.. _auth-extra-responses:

Extra responses
---------------

Every auth automatically documents the ``401`` it can produce.
If yours can fail in some other way, say so by overriding
:meth:`~dmr.metadata.ResponseSpecProvider.provide_response_specs`,
and the OpenAPI schema will list it:

.. code:: python

  @override
  def provide_response_specs(
      self,
      metadata: EndpointMetadata,
      controller_cls: type[Controller[BaseSerializer]],
      existing_responses: Mapping[HTTPStatus, ResponseSpec],
  ) -> list[ResponseSpec]:
      return [
          # Keep the `401` that every auth declares:
          *self._add_new_response(
              unauth_response_spec(controller_cls),
              existing_responses,
          ),
          *self._add_new_response(
              ResponseSpec(
                  controller_cls.error_model,
                  status_code=HTTPStatus.FORBIDDEN,
                  description='Raised when the proxy signature is invalid',
              ),
              existing_responses,
          ),
      ]

Two things to notice:

- Overriding this replaces the default entirely, so call
  :func:`~dmr.security.base.unauth_response_spec` yourself to keep
  the ``401``
- ``_add_new_response`` is protected on purpose: it is meant for
  subclasses like yours. It skips a response the endpoint already
  declares, so you never fight with the endpoint's own specs

This is how our cookie-based auth documents the ``403`` that its CSRF
check can return.


Sync and async
--------------

Sync and async auth are separate classes: a sync controller cannot use
async auth, and the other way around. So an auth meant for both ends up
as a pair, with the shared parts in a common base:

.. literalinclude:: /examples/auth/custom/async_auth.py
  :caption: async_auth.py
  :linenos:
  :language: python

Note that only the parts that touch the database differ. Everything
else, including the whole OpenAPI description, comes from
``BaseProxyHeaderAuth``.

When you set auth globally and your project has both kinds of
endpoints, wrap the pair in :class:`~dmr.security.SyncOrAsyncAuth`:

.. code-block:: python
  :caption: settings.py

  from dmr.settings import Settings
  from dmr.security import SyncOrAsyncAuth

  from your_app.auth import ProxyHeaderAsyncAuth, ProxyHeaderSyncAuth

  DMR_SETTINGS = {
      Settings.auth: [
          SyncOrAsyncAuth(
              ProxyHeaderSyncAuth(),
              ProxyHeaderAsyncAuth(),
          ),
      ],
  }


Rules to follow
---------------

Instances must be stateless
~~~~~~~~~~~~~~~~~~~~~~~~~~~

One instance serves every request. It can live in ``DMR_SETTINGS`` and
be shared by every controller in the project, across threads and
coroutines.

So configuration set in ``__init__`` is fine, but anything per-request
is not. Not even a lock. Put per-request data on the request, like
``set_request_attrs`` does above.

``__init__`` must work with no arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every parameter needs a default, so ``YourAuth()`` alone is always
valid. Make them keyword-only while you are at it, the way our classes
do, so adding a parameter later never breaks anyone.

Define ``__slots__``
~~~~~~~~~~~~~~~~~~~~

Auth classes are instantiated once but touched on every request, and we
enforce ``__slots__`` on our own classes in CI. Declare the attributes
on the class that assigns them, and leave ``__slots__ = ()`` on the
subclasses that add none.

Keep credentials out of error reports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Anything your auth holds in a local variable shows up in tracebacks
that error reporting middlewares send to admins. If your auth handles
raw secrets, decorate the methods that touch them with
:func:`django.views.decorators.debug.sensitive_variables`.

See :ref:`the auth views section <auth-views-security>` for the details,
they apply to auth classes just as much as to views.


API Reference
-------------

.. autofunction:: dmr.security.base.unauth_response_spec


Next up
-------

Once your auth works, everything else we document applies to it
unchanged. You will probably want:

- :doc:`common` for how auth is enabled, chained, and disabled
- :doc:`/pages/testing/authentication` for testing endpoints behind it
- :doc:`/pages/openapi/openapi` for the generated schema
