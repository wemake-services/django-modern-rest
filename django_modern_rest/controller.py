from typing import Any, ClassVar

from django.views import View


class Controller(View):
    """Defines API views as controllers."""

    # TODO: use TypedDict
    model_dump_json_kwargs: ClassVar[dict[str, Any]] = {}
