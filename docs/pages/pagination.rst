.. _pagination:

Pagination
==========

``django-modern-rest`` supports two main pagination patterns:

- **Limit/offset** pagination,
  based on the built-in :class:`django.core.paginator.Paginator`
- **Cursor** (also known as keyset or seek) pagination,
  based on the first-party :class:`~dmr.pagination.CursorPaginator`

Use limit/offset for simple and relatively small collections.
Use cursor pagination for large tables and for feeds
that keep receiving new rows
while a client is paging through them.


Limit offset
------------

We support the built-in :class:`django.core.paginator.Paginator`.

To do so, we only provide metadata for the default pagination:

.. literalinclude:: /examples/integrations/pagination.py
  :caption: views.py
  :language: python
  :linenos:

If you are using a different pagination system, you can define
your own metadata / models and use them with our framework.


Cursor
------

Cursor pagination works by remembering the position of the last seen row
and asking the database for the next batch of rows after that position.

Unlike limit/offset, it does not use ``OFFSET``,
so it stays fast even on very large tables,
and it never skips or duplicates rows
when new data is inserted in the middle of a collection.

The built-in :class:`~dmr.pagination.CursorPaginator`
works directly with :class:`~django.db.models.query.QuerySet`
and has both sync and async APIs.

.. important::

  The paginator requires a stable ordering.
  Set ``.order_by()`` on your queryset
  before creating the paginator.
  The primary key fields are appended automatically as tiebreakers,
  so your ``order_by`` fields do not have to be unique.

Model
~~~~~

.. literalinclude:: ../../django_test_app/server/apps/model_cursor/models.py
  :caption: models.py
  :language: python
  :linenos:

Views
~~~~~

Here is an example of a list endpoint with cursor pagination:


.. tabs::

  .. tab:: sync

    .. literalinclude:: ../../django_test_app/server/apps/model_cursor/views.py
      :caption: views.py
      :language: python
      :linenos:

  .. tab:: async

    .. literalinclude:: ../../django_test_app/server/apps/model_cursor/async_views.py
      :caption: views.py
      :language: python
      :linenos:

The async variant is identical,
except that it uses ``await paginator.apage(cursor)``
instead of ``paginator.page(cursor)``.

What happens here:

1. The query accepts ``cursor`` and ``page_size``
2. The paginator is created over the queryset,
   ordered by ``rank`` and ``name``
3. ``.page()`` (or ``await .apage()``)
   returns a :class:`~dmr.pagination.CursorPage`
4. The page is mapped to the response model
   :class:`~dmr.pagination.CursorPaginated`

Client protocol
~~~~~~~~~~~~~~~

1. The first request is made without the ``cursor`` parameter
2. The response contains ``next_cursor``
3. To fetch the next page,
   pass ``next_cursor`` back as the ``cursor`` parameter
4. Repeat until ``next_cursor`` becomes ``null``

The response shape looks like this:

.. code-block:: json
  :caption: response.json

  {
      "next_cursor": "MnwtfGF8LXwy",
      "per_page": 2,
      "page": [
          {"rank": 1, "name": "c"},
          {"rank": 2, "name": "a"}
      ]
  }

.. note::

  ``next_cursor`` is ``null`` only when the page has fewer items
  than ``per_page``.
  If the total number of items is an exact multiple of ``per_page``,
  one extra request will return an empty page
  with ``next_cursor`` set to ``null``.

.. warning::

  A cursor is bound to the ordering it was created with.
  If you expose a dynamic ``order_by`` or filters,
  the client must not change them while following a cursor:
  the cursor values will be compared against the new ordering,
  and the client will silently receive wrong rows.
  The request fails with ``400 Bad Request``
  only when the number of ordered fields changes.

How it works
~~~~~~~~~~~~

- The cursor is an encoded tuple of the ordered field values
  of the last row of the previous page
- By default it is encoded with ``base64.urlsafe_b64encode``,
  so the result only contains URL-safe characters;
  the values are joined with the ``|-|`` separator
- The next page is fetched with a single range query
  over the ordered fields,
  a lexicographic comparison of the whole tuple
- Because the primary key fields are always appended as tiebreakers,
  two rows can never share the same cursor position

Unlike many other cursor pagination implementations,
the fields in your ``order_by`` do not have to be unique:
it is enough to order by a plain non-unique field
like ``created_at`` or ``rank``,
because the primary key fields are appended to the ordering
as tiebreakers automatically.

This works because the range query is not a single comparison,
but a disjunction over the whole ordering tuple.
For a queryset ordered by ``rank``
(with the primary key appended as a tiebreaker),
the paginator builds:

.. code-block:: sql

    (rank > cursor.rank)
    OR (rank = cursor.rank AND pk > cursor.pk)

The first branch matches every row strictly after the cursor position.
The second branch matches rows that share the same ``rank`` value,
ordered by the primary key.
Every extra ordering field extends the chain in the same way.

Customizing the cursor format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can pass your own ``cursor_encoder`` and ``cursor_decoder``
functions, as well as a custom ``separator``.
For example, you can encrypt your cursor values to not expose any details and
prevent people from forging cursor values:

.. literalinclude:: /examples/integrations/custom_cursor_encoding.py
  :caption: models.py
  :language: python
  :linenos:

.. note::

  By default cursors are encoded with ``base64.urlsafe_b64encode``,
  so they only contain URL-safe characters
  and can be passed in query strings as-is.
  If you switch to a different alphabet,
  like plain ``base64.b64encode`` with its ``+`` and ``/`` characters,
  they must be percent-encoded by the client.

Errors
~~~~~~

A cursor is a client-provided value.
When it cannot be decoded,
or when it contains a different number of fields than expected,
the paginator raises :exc:`~dmr.pagination.cursor.InvalidCursorError`.

Unlike other framework errors,
it is not handled by the default
:func:`~dmr.errors.global_error_handler` on purpose.
You should catch it in your view
and convert it to an error response yourself.

Alternatively, you can handle the error
in :meth:`~dmr.controller.Controller.handle_error`
or in a custom global error handler,
see :doc:`error-handling` for details.

If your endpoint can return this error,
remember to document the ``400`` status code
in its :class:`~dmr.metadata.ResponseSpec` definitions.


Other libraries
~~~~~~~~~~~~~~~

Any other Django-compatible pagination tool should work out of the box.
Like `django-cursor-pagination <https://github.com/photocrowd/django-cursor-pagination>`_
or even your custom implementation.


API Reference
-------------

Limit offset
~~~~~~~~~~~~

.. autoclass:: dmr.pagination.Paginated
  :members:

.. autoclass:: dmr.pagination.Page
  :members:

Cursor
~~~~~~

.. autoclass:: dmr.pagination.CursorPaginator
  :members:
  :inherited-members:
  :special-members: __init__

.. autoclass:: dmr.pagination.CursorPage
  :members:

.. autoclass:: dmr.pagination.CursorPaginated
  :members:

.. autoclass:: dmr.pagination.cursor.InvalidCursorError
  :members:
