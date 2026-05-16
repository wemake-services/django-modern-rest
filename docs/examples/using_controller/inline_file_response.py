import io

from django.http import FileResponse

from dmr import Controller, validate
from dmr.files import FileResponseSpec
from dmr.plugins.pydantic import PydanticSerializer
from dmr.renderers import FileRenderer


class InlineFileController(Controller[PydanticSerializer]):
    @validate(
        FileResponseSpec(),
        renderers=[FileRenderer('text/plain')],
    )
    def get(self) -> FileResponse:
        return FileResponse(
            io.BytesIO(b'Hello'),
            content_type='text/plain',
        )


# run: {"controller": "InlineFileController", "method": "get", "url": "/api/file/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
# openapi: {"controller": "InlineFileController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
