from typing import Any, ClassVar

from django.utils.functional import cached_property, classproperty
from django.views import View


class Controller(View):
    """Defines API views as controllers."""

    # TODO: use TypedDict
    return_dto_kwargs: ClassVar[dict[str, Any]] = {}

    @cached_property
    @classproperty
    def existing_http_methods(cls) -> set[str]:  # noqa: N805
        """Returns and caches what HTTP methods are implemented in this view."""
        return {
            method
            for method in cls.http_method_names
            if getattr(cls, method, None) is not None
        }
