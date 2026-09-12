from django.contrib.admindocs.utils import parse_docstring


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
