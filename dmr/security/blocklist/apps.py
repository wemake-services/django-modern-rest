from django.apps import AppConfig


class BlocklistConfig(AppConfig):
    """AppConfig for blocklist app."""

    name = 'dmr.security.blocklist'
    verbose_name = 'Token Blocklist'
    default_auto_field = 'django.db.models.BigAutoField'
