from collections.abc import Sequence
from typing import Literal

from django.http import HttpRequest


def check_sensitive_parameters(
    request: HttpRequest,
    expected: Sequence[str] | Literal['__ALL__'] = '__ALL__',
) -> None:
    assert request.sensitive_post_parameters == expected  # type: ignore[attr-defined] # noqa: S101
