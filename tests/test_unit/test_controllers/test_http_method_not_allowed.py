import pytest

from django_modern_rest import (
    Controller,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer
from django_modern_rest.test import DMRRequestFactory


class _WrongController(Controller[PydanticSerializer]):
    def get(self) -> None:
        self.http_method_not_allowed(self.request)  # type: ignore[deprecated]


def test_http_method_not_allowed(dmr_rf: DMRRequestFactory) -> None:
    """Ensure that `http_method_not_allowed` is not allowed to be called."""
    request = dmr_rf.get('/whatever/')

    # pyrefly: ignore[bad-argument-type,no-matching-overload]
    with pytest.raises(
        (DeprecationWarning, NotImplementedError),
        match='handle_method_not_allowed',
    ):
        _WrongController.as_view()(request)
