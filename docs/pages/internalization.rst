Internalization
===============

``django-modern-rest`` support optional ``i18n`` feature
which is provided by the Django itself.

Docs: https://docs.djangoproject.com/en/stable/topics/i18n/

.. note::

  If no configuration is specified, we default to ``en-us`` locale.
  If you just want to use the default language, you don't have to do anything.

Core features:

- Setting default language for everything with a single
  `LANGUAGE_CODE <https://docs.djangoproject.com/en/stable/ref/settings/#language-code>`_
  configuration variable
- Using :class:`django.middleware.locale.LocaleMiddleware` to set
  language per-request based on ``Accept-Language`` header


Enabling translated API messages
--------------------------------

Setting the default language code for all users:

.. code-block:: python
  :caption: settings.py

  LANGUAGE_CODE = 'ru-ru'

Setting the language code per request:

.. code-block:: python
  :caption: settings.py

  MIDDLEWARE = [
      # ...
      'django.middleware.locale.LocaleMiddleware'
  ]

Then any requests with ``Accept-Language`` header will set
the required language for this specific response.

Specifying the list of the supported languages:

.. code-block:: python
  :caption: settings.py

  from django.utils.translation import gettext_lazy as _

  LANGUAGES = [
      ('it', _('Italian')),
      ('en', _('English')),
  ]

.. important::

  Whenever you use Django's builtin translation feature, don't forget to run
  `compilemessages <https://docs.djangoproject.com/en/stable/ref/django-admin/#compilemessages>`_
  management command before using the translations.


Forcing constant API language
-----------------------------

If you have a website using some non-english ``LANGUAGE_CODE``
and you want to add an API that will always use

.. literalinclude:: /examples/internalization/force_en.py
  :caption: middleware.py
  :language: python
  :linenos:

And then add it to your `MIDDLEWARE <https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-MIDDLEWARE>`_
setting:

.. code-block:: python
  :caption: settings.py

  MIDDLEWARE = [
      # ...
      'path.to.ForceEnglishForAPI',
      # ...
  ]


Adding local translations
-------------------------

If you are using a language that is not supported by ``django-modern-rest``
natively, you can translate them right in your own local project.

Here's how to do it:

1. Create a directory called ``locale/`` inside your project and add it to
   `LOCALE_PATHS <https://docs.djangoproject.com/en/6.0/ref/settings/#locale-paths>`_
   setting in ``settings.py``
2. Create a language directory inside ``locale/``,
   for example: ``locale/pt-br/``,
   with the locale name that you want to support.
   See `ISO 639 <https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes>`_
   for the list of the language codes
3. Take the initial `translation template <https://github.com/wemake-services/django-modern-rest/blob/master/dmr/locale/en_US/LC_MESSAGES/django.po>`_
   from our repository
4. Fill in the translations
5. Run ``python manage.py compilemessages -l pt-br``,
   where ``pt-br`` is the locale you want to support
6. Restart your development server with
   ``python manage.py runserver``, if you want to see the changes

Please, contribute your translation back to ``django-modern-rest``!
It would be a good addition to the library.
