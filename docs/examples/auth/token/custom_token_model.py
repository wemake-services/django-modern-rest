from django.db import models
from typing_extensions import override

from dmr.security.token import HeaderTokenSyncAuth
from dmr.security.token.models import Token


class ProjectToken(Token):
    """Extends Token with an extra project FK."""

    project = models.ForeignKey(  # type: ignore[var-annotated]
        'myapp.Project',
        on_delete=models.CASCADE,
        related_name='tokens',
    )

    class Meta:
        app_label = 'myapp'


class ProjectTokenAuth(HeaderTokenSyncAuth):
    @override
    def token_model(self) -> type[Token]:
        return ProjectToken
