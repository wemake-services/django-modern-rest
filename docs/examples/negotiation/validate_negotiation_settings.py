from dmr.settings import Settings, default_parser, default_renderer
from examples.negotiation.negotiation import XmlParser, XmlRenderer

DMR_SETTINGS = {  # noqa: WPS407
    Settings.parsers: [XmlParser(), default_parser],
    Settings.renderers: [XmlRenderer(), default_renderer],
    Settings.validate_negotiation: False,
}
