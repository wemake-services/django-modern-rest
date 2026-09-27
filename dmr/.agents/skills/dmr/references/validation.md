# Validation and configuration

Reference for the `dmr` skill. Loaded on demand, see [SKILL.md](../SKILL.md).


## Validation

### Disable response validation in production, keep it on in development

Response validation catches schema mismatches during development, but adds overhead in production — disable it globally for deployed apps.

Wrong:

```python
# settings.py — production with validation still on (slow):
DMR_SETTINGS = {}  # validate_responses defaults to True
```

Correct:

```python
# settings.py — production:
from dmr.settings import Settings

DMR_SETTINGS = {
    Settings.validate_responses: False,
}
```

**Limitations:** only disable for production — fix schema errors during development instead of turning off validation.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/validation.html

### Do not disable response validation when retuning extra data

Instead of disabling response validation when retuning some extra data,
add new `ResponseSpec` objects.

Wrong:

```python
from http import HTTPStatus

from dmr import APIError, Body, Controller
from dmr.plugins.msgspec import MsgspecSerializer


class MyController(Controller[MsgspecSerializer]):
    validate_responses = False

    def post(self, parsed_body: Body[dict[str, str]]) -> str:
        if not parsed_body:
            raise APIError(
                self.format_error('empty body'),
                status_code=HTTPStatus.GONE,
            )
        return 'saved'
```

Correct:

```python
from http import HTTPStatus

from dmr import APIError, Body, Controller, ResponseSpec, modify
from dmr.plugins.msgspec import MsgspecSerializer


class MyController(Controller[MsgspecSerializer]):
    @modify(
        extra_responses=[
            ResponseSpec(
                return_type=Controller.error_model,
                status_code=HTTPStatus.GONE,
            ),
        ],
    )
    def post(self, parsed_body: Body[dict[str, str]]) -> str:
        if not parsed_body:
            raise APIError(
                self.format_error('empty body'),
                status_code=HTTPStatus.GONE,
            )
        return 'saved'
```

### Don't override `HttpSpec` validation unless implementing legacy APIs

`HttpSpec` validation is already disabled by default for problematic cases — overriding it should only be done for very specific legacy API compatibility reasons.

Wrong:

```python
from http import HTTPStatus

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer
from dmr.settings import HttpSpec


class JobController(Controller[PydanticSerializer]):
    # Disabling just to avoid fixing the real issue:
    no_validate_http_spec = frozenset((HttpSpec.empty_response_body,))

    @modify(status_code=HTTPStatus.NO_CONTENT)
    def post(self) -> int:
        return 4
```

Correct:

```python
from http import HTTPStatus

from dmr import Controller, modify
from dmr.plugins.pydantic import PydanticSerializer


class JobController(Controller[PydanticSerializer]):
    @modify(status_code=HTTPStatus.NO_CONTENT)
    def post(self) -> None:
        print('Job created')  # noqa: WPS421
```

**Limitations:** override `no_validate_http_spec` only when implementing old legacy APIs that cannot follow HTTP spec properly.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/validation.html


## Configuration

### Do not disable `semantic_responses`

`semantic_responses=True` (default) automatically injects common error responses (auth errors, validation errors, throttling) into your OpenAPI schema.

Wrong:

```python
# settings.py — no semantic responses, error schemas missing from OpenAPI:
from dmr.settings import Settings

DMR_SETTINGS = {
    Settings.semantic_responses: False,
}
```

Correct: do not override this setting, unless 100% required.

**Limitations:** you can exclude specific status codes from semantic responses using `Settings.exclude_semantic_responses` if they don't apply to your API.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/configuration.html

### Always have at least one default parser and renderer in settings

Settings must always include at least one parser and one renderer for fallback error handling — even if you override parsers/renderers on controllers.

Wrong:

```python
# settings.py — no parsers/renderers at all:
from dmr.settings import Settings

DMR_SETTINGS = {
    Settings.parsers: [],
    Settings.renderers: [],
}
```

Correct:

```python
# settings.py:
from dmr.settings import Settings

DMR_SETTINGS = {
    # Default JSON parsers/renderers are included automatically
    # when not specified — don't set empty lists.
}
```

**Limitations:** custom parsers and renderers can be added per-controller or per-endpoint on top of the global defaults.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/configuration.html
