from django.apps import AppConfig


class TokenConfig(AppConfig):
    """AppConfig for token auth app."""

    name = 'dmr.security.token'
    verbose_name = 'Token Auth'
    default_auto_field = 'django.db.models.BigAutoField'
