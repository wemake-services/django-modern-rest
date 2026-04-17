from dmr.settings import Settings
from examples.negotiation.negotiation import XmlParser, XmlRenderer

DMR_SETTINGS = {  # noqa: WPS407
    Settings.parsers: [XmlParser()],
    Settings.renderers: [XmlRenderer()],
}
