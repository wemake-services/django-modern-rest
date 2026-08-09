import pathlib
from typing import Any

import yaml


def read_openapi_yaml(filename: str) -> dict[str, Any]:
    return yaml.safe_load(  # type: ignore[no-any-return]
        pathlib.Path(f'examples/external_views/{filename}').read_text(
            encoding='utf8',
        ),
    )
