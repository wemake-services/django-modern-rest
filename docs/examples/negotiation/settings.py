from dmr.settings import Settings
from examples.negotiation.negotiation import XmlParser, XmlRenderer

DMR_SETTINGS = {  # noqa: WPS407
    # You can also use string fully qualified names to import them:
    Settings.parsers: [XmlParser()],
    Settings.renderers: [XmlRenderer()],
}
