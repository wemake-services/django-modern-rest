from typing import Any, final, ClassVar

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest
from django.utils.http import parse_header_parameters
from typing_extensions import override

from dmr.parsers import DeserializeFunc, Parser, Raw, SupportsFileParsing


@final
class OctetStreamParser(SupportsFileParsing, Parser):
    """
    Parses ``application/octet-stream`` raw file uploads.

    Populates ``request.FILES`` with a ``SimpleUploadedFile`` created
    from the raw request body.
    """

    __slots__ = ()

    content_type = 'application/octet-stream'
    default_field_name: ClassVar[str] = 'field_name'
    default_filename: ClassVar[str] = 'file'

    @override
    def parse(
        self,
        to_deserialize: Raw,
        deserializer_hook: DeserializeFunc | None = None,
        *,
        request: HttpRequest,
        model: Any,
    ) -> None:
        """Populate ``request.FILES`` from raw request body."""
        content_disposition = request.headers.get('Content-Disposition')
        if content_disposition:
            _, disposition_params = parse_header_parameters(content_disposition)
        else:
            disposition_params = {}

        field_name = disposition_params.get('name') or self.default_field_name
        filename = disposition_params.get('filename') or self.default_filename

        # It does not support multiple files by design,
        # because it is designed to be a single-file upload feature:
        request.FILES[field_name] = SimpleUploadedFile(
            filename,
            request.body,
            content_type=self.content_type,
        )
