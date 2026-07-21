import json
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from typing_extensions import override

if TYPE_CHECKING:
    from sphinx.writers.html5 import HTML5Translator


class ChartJSNode(nodes.General, nodes.Element):
    """Custom node for Chart.js diagrams."""


class ChartJSDirective(SphinxDirective):
    """Directive for embedding Chart.js diagrams.

    Usage::

        .. chartjs:: Chart Title

            {
              "light": {
                "type": "bar",
                "data": {...},
                "options": {...}
              },
              "dark": {
                "type": "bar",
                "data": {...},
                "options": {...}
              }
            }
    """

    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = True

    @override
    def run(self) -> list[nodes.Node]:
        """Process the directive."""
        if not self.content:
            return []

        json_content = '\n'.join(self.content)
        try:
            chart_config = json.loads(json_content)
        except json.JSONDecodeError as exc:
            error = self.state_machine.reporter.error(
                f'Invalid JSON in chartjs directive: {exc}',
                nodes.literal_block(json_content, json_content),
                line=self.lineno,
            )
            return [error]

        node = ChartJSNode()
        node['chart_id'] = f'chartjs-{abs(hash(json_content))}'
        node['chart_config'] = json.dumps(chart_config)
        node['title'] = self.arguments[0] if self.arguments else ''
        return [node]


def _visit_chartjs_html(self: 'HTML5Translator', node: ChartJSNode) -> None:
    """Visit ChartJS node for HTML output."""
    title = node.get('title', '')
    if title:
        self.body.append(f'<h3>{self.encode(title)}</h3>\n')
    self.body.append(f'<canvas id="{node["chart_id"]}"></canvas>\n')
    self.body.append(
        '<script type="application/json" data-chartjs-config '
        f'data-chartjs-target="{node["chart_id"]}">'
        f'{node["chart_config"]}</script>\n',
    )


def _depart_chartjs_html(self: 'HTML5Translator', node: ChartJSNode) -> None:
    """Depart ChartJS node for HTML output."""


def setup(app: Sphinx) -> None:
    """Setup Chart.js directive."""
    app.add_node(ChartJSNode, html=(_visit_chartjs_html, _depart_chartjs_html))
    app.add_js_file('js/chartjs.js')
