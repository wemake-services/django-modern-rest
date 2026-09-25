"""
Markdown handlers for the nodes that ``sphinx_llm_friendly`` does not know.

It writes a Markdown version of every page and ``llms-full.txt``
during the HTML build, and drops every node type without a handler
with a warning, which fails our ``-W`` build.
Our own nodes register their handlers where they are defined,
this module covers the third-party ones.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from docutils import nodes
from sphinx.application import Sphinx
from sphinx_iconify.roles import iconify_icon  # type: ignore[import-untyped]
from sphinxcontrib.mermaid import mermaid  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from sphinx.util.docutils import SphinxTranslator
    from sphinx_llm_friendly._translator import MarkdownTranslator  # type: ignore[import-untyped]


def skip_node(self: SphinxTranslator, node: nodes.Node) -> NoReturn:
    """Leave the node and its children out, they carry no text for readers."""
    raise nodes.SkipNode


def _visit_mermaid(self: MarkdownTranslator, node: nodes.Element) -> NoReturn:
    """Diagrams are kept as fenced ``mermaid`` blocks, LLMs read them."""
    self.add('```mermaid', prefix_eol=2, suffix_eol=1)
    self.add(str(node['code']))
    self.add('```', prefix_eol=1, suffix_eol=2)
    raise nodes.SkipNode


def setup(app: Sphinx) -> None:
    """Register handlers, ``override`` because the nodes exist already."""
    app.add_node(mermaid, override=True, llm_markdown=(_visit_mermaid, None))
    app.add_node(iconify_icon, override=True, llm_markdown=(skip_node, None))
    # The author of the epigraph on the landing page:
    app.add_node(
        nodes.attribution,
        override=True,
        llm_markdown=(skip_node, None),
    )
