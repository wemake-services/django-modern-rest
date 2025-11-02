from __future__ import annotations

from auto_pytabs.sphinx_ext import CodeBlockOverride
from sphinx.application import Sphinx

from tools.sphinx_ext import chartjs, run_examples


def _register_directives(app: Sphinx) -> None:
    """Directives registered after all extensions have been loaded."""
    app.add_directive(
        'literalinclude',
        run_examples.LiteralInclude,
        override=True,
    )
    app.add_directive('code-block', CodeBlockOverride, override=True)


def setup(app: Sphinx) -> dict[str, bool]:
    """Initialize Sphinx extensions and return configuration."""
    app.connect('builder-inited', _register_directives)
    chartjs.setup(app)
    return run_examples.setup(app)
