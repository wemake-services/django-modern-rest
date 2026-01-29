try:
    import pydantic  # noqa: F401  # pyright: ignore[reportUnusedImport]
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pydantic` is not installed, '
        "consider using `pip install 'django-modern-rest[pydantic]'`",
    )
    raise

from django_modern_rest.plugins.pydantic.extractor import (
    PydanticFieldExtractor as PydanticFieldExtractor,
)
from django_modern_rest.plugins.pydantic.serializer import (
    FromPythonKwargs as FromPythonKwargs,
)
from django_modern_rest.plugins.pydantic.serializer import (
    ModelDumpKwargs as ModelDumpKwargs,
)
from django_modern_rest.plugins.pydantic.serializer import (
    PydanticEndpointOptimizer as PydanticEndpointOptimizer,
)
from django_modern_rest.plugins.pydantic.serializer import (
    PydanticErrorModel as PydanticErrorModel,
)
from django_modern_rest.plugins.pydantic.serializer import (
    PydanticSerializer as PydanticSerializer,
)
from django_modern_rest.plugins.pydantic.serializer import (
    _get_cached_type_adapter as _get_cached_type_adapter,  # pyright:ignore[reportPrivateUsage]
)
