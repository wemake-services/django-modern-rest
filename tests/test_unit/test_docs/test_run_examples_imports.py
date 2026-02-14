from importlib import util
from pathlib import Path
from typing import Any, cast

EXPECTED_HIDDEN_LINES = 12
EXPECTED_START_LINE = 13

EXAMPLE_SOURCE: str = """import uuid
from typing import final

import pydantic

from django_modern_rest import (  # noqa: WPS235
    Blueprint,
    Body,
)
from django_modern_rest.plugins.pydantic import PydanticSerializer


class _UserInput(pydantic.BaseModel):
    email: str
    age: int
"""


def _load_run_examples_module() -> Any:
    module_path = (
        Path(__file__).resolve().parents[3]
        / 'docs'
        / 'tools'
        / 'sphinx_ext'
        / 'run_examples.py'
    )
    spec = util.spec_from_file_location(
        'run_examples_for_test',
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    run_examples = util.module_from_spec(spec)
    spec.loader.exec_module(run_examples)
    return run_examples


def _extract_hidden_lines(
    run_examples: Any,
) -> tuple[list[str], int]:
    source_lines = EXAMPLE_SOURCE.splitlines()
    imports_end = cast(
        int,
        run_examples._find_imports_block_end_line(EXAMPLE_SOURCE),
    )
    hidden_until = cast(
        int,
        run_examples._extend_with_trailing_blank_lines(
            source_lines,
            imports_end,
        ),
    )
    return source_lines[:hidden_until], hidden_until + 1


def _get_summary_text(
    run_examples: Any,
    hidden_lines: list[str],
) -> str:
    directive = object.__new__(run_examples.LiteralInclude)
    directive.options = {}
    return cast(str, directive._get_imports_summary_text(hidden_lines))


def test_extract_imports_hides_trailing_blanks() -> None:
    """Ensures trailing blank lines after imports are hidden too."""
    run_examples = _load_run_examples_module()
    hidden_lines, start_line = _extract_hidden_lines(run_examples)

    assert len(hidden_lines) == EXPECTED_HIDDEN_LINES
    assert start_line == EXPECTED_START_LINE

    assert _get_summary_text(run_examples, hidden_lines) == (
        'Show imports... 12 lines hidden'
    )
