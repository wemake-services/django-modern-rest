# OpenAPI

Reference for the `dmr` skill. Loaded on demand, see [SKILL.md](../SKILL.md).


## OpenAPI

### Add docstrings to controllers and endpoints for OpenAPI descriptions

Controller and endpoint docstrings are automatically used as descriptions in the generated OpenAPI schema.

Wrong:

```python
from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class UserController(Controller[PydanticSerializer]):
    def get(self) -> str:
        return 'hello'

    def post(self) -> str:
        return 'created'
```

Correct:

```python
from dmr import Controller
from dmr.plugins.pydantic import PydanticSerializer


class UserController(Controller[PydanticSerializer]):
    """Manage user accounts."""

    def get(self) -> str:
        """Retrieve the current user profile."""
        return 'hello'

    def post(self) -> str:
        """Create a new user account."""
        return 'created'
```

**Limitations:** docstrings only populate the `description` field in OpenAPI — use `@modify` or `@validate` for operation-level customization of other OpenAPI fields.

Docs: https://django-modern-rest.readthedocs.io/en/latest/pages/openapi/openapi.html
