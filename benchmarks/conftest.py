import os

import django
from django.conf import settings


def pytest_configure() -> None:
    """Configure Django settings for benchmarks."""
    if not settings.configured:
        os.environ.setdefault(
            'DJANGO_SETTINGS_MODULE',
            'benchmark_settings',
        )
        settings.configure(
            ROOT_URLCONF='benchmarks.apps.dmr',
            DMR_SETTINGS={'validate_responses': False},
            ALLOWED_HOSTS=['*'],
            DEBUG=False,
            SECRET_KEY='benchmark-secret-key',
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'dmr',
            ],
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                },
            },
        )
        django.setup()
