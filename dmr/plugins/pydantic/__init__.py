try:
    import pydantic  # noqa: F401  # pyright: ignore[reportUnusedImport]
except ImportError:  # pragma: no cover
    print(  # noqa: WPS421
        'Looks like `pydantic` is not installed, '
        "consider using `pip install 'django-modern-rest[pydantic]'`",
    )
    raise

from dmr.plugins.pydantic.extractor import (
    PydanticFieldExtractor as PydanticFieldExtractor,
)
from dmr.plugins.pydantic.serializer import (
    FromPythonKwargs as FromPythonKwargs,
)
from dmr.plugins.pydantic.serializer import (
    ModelDumpKwargs as ModelDumpKwargs,
)
from dmr.plugins.pydantic.serializer import (
    PydanticEndpointOptimizer as PydanticEndpointOptimizer,
)
from dmr.plugins.pydantic.serializer import (
    PydanticSerializer as PydanticSerializer,
)
