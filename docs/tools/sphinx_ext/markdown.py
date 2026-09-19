"""
Markdown output for the nodes that ``sphinx_markdown_builder`` does not know.

We publish a Markdown twin of every documentation page for LLMs and agents
(see ``markdown`` in ``docs/justfile`` and ``.readthedocs.yml``).
The builder warns and drops every node type it has no handler for,
this module registers handlers for our own nodes and for the third-party
ones we use, so the Markdown build is clean under ``-W``
and the content survives the conversion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.application import Sphinx
from sphinx_design.shared import PassthroughTextElement
from sphinx_iconify.roles import iconify_icon
from sphinxcontrib.mermaid import mermaid

from tools.sphinx_ext import chartjs, run_examples

if TYPE_CHECKING:
    from sphinx_markdown_builder.translator import MarkdownTranslator


def _noop(self: MarkdownTranslator, node: nodes.Node) -> None:
    """Render the children, add nothing for the node itself."""


def _skip(self: MarkdownTranslator, node: nodes.Node) -> None:
    """Drop the node and its children, they carry no text for readers."""
    raise nodes.SkipNode


def _visit_admonition(self: MarkdownTranslator, node: nodes.Element) -> None:
    """Titled admonition, rendered like the builder renders ``note``."""
    title = node.next_node(nodes.title)
    box_title = 'NOTE'
    if title is not None:
        node.remove(title)
        box_title = title.astext()
    self._push_box(box_title)


def _depart_admonition(self: MarkdownTranslator, node: nodes.Element) -> None:
    self._pop_context()


def _visit_caption(self: MarkdownTranslator, node: nodes.Element) -> None:
    """Figure and code-block captions become an emphasized line."""
    self.add('*', prefix_eol=1)


def _depart_caption(self: MarkdownTranslator, node: nodes.Element) -> None:
    self.add('*', suffix_eol=2)


def _depart_abbreviation(
    self: MarkdownTranslator,
    node: nodes.Element,
) -> None:
    """Keep the explanation of ``:abbr:`` roles in parentheses."""
    explanation = node.get('explanation')
    if explanation:
        self.add(f' ({explanation})')


def _visit_attribution(self: MarkdownTranslator, node: nodes.Element) -> None:
    """Quote attribution, as in the epigraph on the landing page."""
    self.add('— ', prefix_eol=1)


def _depart_attribution(self: MarkdownTranslator, node: nodes.Element) -> None:
    self.ensure_eol(2)


def _visit_mermaid(self: MarkdownTranslator, node: nodes.Element) -> None:
    """Diagrams are kept as fenced ``mermaid`` blocks, LLMs read them."""
    self.add('```mermaid', prefix_eol=2, suffix_eol=1)
    self.add(str(node.get('code') or node.astext()))
    self.add('```', prefix_eol=1, suffix_eol=2)
    raise nodes.SkipNode


def _visit_chartjs(self: MarkdownTranslator, node: nodes.Element) -> None:
    """Charts are interactive, point readers to the HTML page."""
    title = node.get('title') or 'Chart'
    self.add(
        f'*{title}: interactive chart, see the HTML version of this page.*',
        prefix_eol=2,
        suffix_eol=2,
    )
    raise nodes.SkipNode


def _visit_github_source_link(
    self: MarkdownTranslator,
    node: nodes.Element,
) -> None:
    """The ``[source]`` link of every executed example."""
    self.add(
        f'[source]({node.get("github_url", "")})',
        prefix_eol=1,
        suffix_eol=1,
    )
    raise nodes.SkipNode


def _visit_toggle_summary(
    self: MarkdownTranslator,
    node: nodes.Element,
) -> None:
    """Summary of a collapsible block becomes a bold line."""
    self.add('**', prefix_eol=2)


def _depart_toggle_summary(
    self: MarkdownTranslator,
    node: nodes.Element,
) -> None:
    self.add('**', suffix_eol=2)


def setup(app: Sphinx) -> None:
    """Register Markdown handlers, ``override`` because nodes exist already."""
    handlers = {
        nodes.admonition: (_visit_admonition, _depart_admonition),
        # The builder drops figures entirely, we want their diagrams:
        nodes.figure: (_noop, _noop),
        nodes.caption: (_visit_caption, _depart_caption),
        nodes.abbreviation: (_noop, _depart_abbreviation),
        nodes.attribution: (_visit_attribution, _depart_attribution),
        mermaid: (_visit_mermaid, _noop),
        iconify_icon: (_skip, _noop),
        PassthroughTextElement: (_noop, _noop),
        chartjs.ChartJSNode: (_visit_chartjs, _noop),
        run_examples._ImportsSpoiler: (_noop, _noop),  # noqa: SLF001
        run_examples._ImportsSpoilerSummary: (_skip, _noop),  # noqa: SLF001
        run_examples._GithubSourceLink: (_visit_github_source_link, _noop),  # noqa: SLF001
        run_examples._OpenAPIResultToggle: (_noop, _noop),  # noqa: SLF001
        run_examples._OpenAPIResultToggleSummary: (  # noqa: SLF001
            _visit_toggle_summary,
            _depart_toggle_summary,
        ),
    }
    for node_class, (visit, depart) in handlers.items():
        app.add_node(node_class, override=True, markdown=(visit, depart))
