Returning redirects
===================

We support returning redirects from API endpoins with
:class:`~dmr.response.APIRedirectError` custom exception:

.. literalinclude:: /examples/returning_responses/redirect_error.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 18-19, 26, 30

And default Django's :class:`django.http.HttpResponseRedirect`:

.. literalinclude:: /examples/returning_responses/redirect_response.py
  :caption: views.py
  :language: python
  :linenos:
  :emphasize-lines: 24
