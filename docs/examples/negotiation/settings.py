from django_modern_rest.settings import Settings
from examples.negotiation.negotiation import XmlParser, XmlRenderer

DMR_SETTINGS = {  # noqa: WPS407
    Settings.parser_types: [XmlParser],
    Settings.renderer_types: [XmlRenderer],
}
