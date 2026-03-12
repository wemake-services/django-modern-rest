from __future__ import annotations

import importlib
import sys
from pathlib import Path

import django
import uvicorn
from django.apps import apps
from django.conf import settings
from django.core.handlers.asgi import ASGIHandler
from django.urls import clear_url_caches


def _configure_paths(docs_dir: Path) -> None:
    project_dir = docs_dir.parent
    django_app_dir = project_dir / 'django_test_app'
    for path in (docs_dir, project_dir, django_app_dir):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _configure_settings() -> None:
    if settings.configured:
        return

    settings.configure(
        ROOT_URLCONF='url_conf',
        ALLOWED_HOSTS=['*'],
        DEBUG=True,
        SECRET_KEY='dummy-key-for-examples',  # noqa: S106
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'dmr',
            'dmr.security.jwt.blocklist',
        ],
        MIDDLEWARE=[],
        USE_TZ=True,
        HTTP_BASIC_USERNAME='admin',
        HTTP_BASIC_PASSWORD='pass',  # noqa: S106
    )
    if not apps.ready:
        django.setup()


def main() -> None:
    """Run a temporary Django app that serves OpenAPI JSON."""
    port = int(sys.argv[1])
    module_name = sys.argv[2]
    docs_dir = Path(sys.argv[3])

    _configure_paths(docs_dir)
    _configure_settings()

    sys.modules.pop(module_name, None)
    importlib.import_module(module_name)
    settings.ROOT_URLCONF = module_name
    clear_url_caches()
    uvicorn.run(
        app=ASGIHandler(),
        port=port,
        access_log=False,
        log_level='error',
    )


if __name__ == '__main__':
    main()
