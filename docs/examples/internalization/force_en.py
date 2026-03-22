from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.utils import translation


class ForceEnglishForAPI:
    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # You can use `router.prefix` here instead:
        if request.path.startswith('/api/'):
            # You can configure this to be
            # `settings.API_LANGUAGE_CODE`
            # and set `API_LANGUAGE_CODE = 'en-us'` in your settings file.
            translation.activate('en-us')  # or any other language
        return self.get_response(request)
