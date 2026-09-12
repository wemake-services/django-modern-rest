from typing import TYPE_CHECKING

from django.contrib.admindocs.utils import parse_docstring
from typing_extensions import Sentinel, TypedDict

if TYPE_CHECKING:
    from django.utils.functional import (
        _StrOrPromise,  # pyright: ignore[reportPrivateUsage]
    )


class SummaryAndDescription(TypedDict, closed=True):
    """Both docs fields of an OpenAPI object, ready to be passed with ``**``."""

    summary: str | None
    description: str | None


def parse_summary_and_description(
    docstring: str | None,
) -> tuple[str | None, str | None]:
    """
    Split a docstring into OpenAPI ``summary`` and ``description`` parts.

    Uses django's ``parse_docstring()`` helper: the first paragraph
    becomes the summary, everything after it becomes the description.

    All empty strings are converted to ``None``.
    """
    summary, description, _ = parse_docstring(docstring or '')
    return summary or None, description or None


def resolve_summary_and_description(
    docstring: str | None,
    summary: '_StrOrPromise | Sentinel | None',
    description: '_StrOrPromise | Sentinel | None',
) -> SummaryAndDescription:
    """
    Resolve explicitly set summary and description against a docstring.

    Each field is resolved on its own: ``EMPTY`` means that the value
    is taken from *docstring*, explicit ``None`` stays ``None``,
    so nothing is generated at all.
    """
    parsed_summary, parsed_description = parse_summary_and_description(
        docstring,
    )
    return {
        'summary': _resolve_doc_field(summary, parsed_summary),
        'description': _resolve_doc_field(description, parsed_description),
    }


def _resolve_doc_field(
    explicit: '_StrOrPromise | Sentinel | None',
    parsed: str | None,
) -> str | None:
    if isinstance(explicit, Sentinel):
        return parsed
    return None if explicit is None else str(explicit)
