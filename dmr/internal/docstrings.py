from django.contrib.admindocs.utils import parse_docstring
from typing_extensions import Sentinel

from dmr.internal.types import StrOrPromise


def resolve_summary_and_description(
    docstring: str | None,
    summary: StrOrPromise | Sentinel | None,
    description: StrOrPromise | Sentinel | None,
) -> tuple[str | None, str | None]:
    """
    Resolve OpenAPI ``summary`` and ``description`` against a docstring.

    Both are resolved on their own, they never affect each other:
    a value left as ``EMPTY`` is taken from *docstring*,
    an explicit ``None`` stays ``None``, so nothing is generated at all.

    Django's ``parse_docstring()`` does the parsing: the first paragraph
    of *docstring* becomes the summary, everything after it becomes
    the description. All empty strings are converted to ``None``.
    """
    parsed_summary, parsed_description, _ = parse_docstring(docstring or '')
    return (
        _resolve_doc_field(summary, parsed_summary or None),
        _resolve_doc_field(description, parsed_description or None),
    )


def _resolve_doc_field(
    explicit: StrOrPromise | Sentinel | None,
    parsed: str | None,
) -> str | None:
    if isinstance(explicit, Sentinel):
        return parsed
    return None if explicit is None else str(explicit)
