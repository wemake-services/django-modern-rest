import json
from typing import TYPE_CHECKING, Final, final

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from typing_extensions import override

if TYPE_CHECKING:
    from sphinx.writers.html5 import HTML5Translator

_SCRIPT: Final = """
<script>
(function() {{
    const chartId = '{chart_id}';
    const canvas = document.getElementById(chartId);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const config = {chart_config};

    // Wait for Chart.js to be loaded
    if (typeof Chart !== 'undefined') {{
        new Chart(ctx, config);
    }} else {{
        window.addEventListener('load', function() {{
            if (typeof Chart !== 'undefined') {{
                new Chart(ctx, config);
            }}
        }});
    }}
}})();
</script>
"""


@final
class ChartJSNode(nodes.General, nodes.Element):
    """Custom node for Chart.js diagrams."""


@final
class ChartJSDirective(SphinxDirective):
    """Directive for embedding Chart.js diagrams.

    Usage::

        .. chartjs:: Chart Title

            {
              "type": "bar",
              "data": {...},
              "options": {...}
            }
    """

    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = True

    @override
    def run(self) -> list[nodes.Node]:  # pyrefly: ignore[bad-override]
        """Process the directive."""
        if not self.content:  # pyrefly: ignore[missing-attribute]
            return []

        json_content = '\n'.join(  # pyrefly: ignore[no-matching-overload]
            self.content,
        )
        try:
            chart_config = json.loads(json_content)
        except json.JSONDecodeError as exc:
            error = self.state_machine.reporter.error(  # pyrefly: ignore[missing-attribute]  # noqa: E501
                f'Invalid JSON in chartjs directive: {exc}',
                nodes.literal_block(json_content, json_content),
                line=self.lineno,  # pyrefly: ignore[missing-attribute]
            )
            return [error]

        node = ChartJSNode()
        node['chart_id'] = f'chartjs-{abs(hash(json_content))}'
        node['chart_config'] = json.dumps(chart_config)
        node['title'] = (
            self.arguments[0]  # pyrefly: ignore[bad-index]
            if self.arguments  # pyrefly: ignore[missing-attribute]
            else ''
        )
        return [node]


def _visit_chartjs_html(self: 'HTML5Translator', node: ChartJSNode) -> None:
    """Visit ChartJS node for HTML output."""
    title = node.get('title', '')
    if title:
        self.body.append(f'<h3>{self.encode(title)}</h3>\n')
    canvas = f'<canvas id="{node["chart_id"]}"></canvas>\n'

    self.body.append(canvas)
    self.body.append(
        _SCRIPT.format(
            chart_id=node['chart_id'],
            chart_config=node['chart_config'],
        ),
    )


def _depart_chartjs_html(self: 'HTML5Translator', node: ChartJSNode) -> None:
    """Depart ChartJS node for HTML output."""


def setup(app: Sphinx) -> None:
    """Setup Chart.js directive."""
    app.add_node(ChartJSNode, html=(_visit_chartjs_html, _depart_chartjs_html))
