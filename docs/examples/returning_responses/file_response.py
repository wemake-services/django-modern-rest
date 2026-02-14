import pathlib
from http import HTTPStatus
from typing import Final, final

from django.http import FileResponse

from django_modern_rest import Controller, HeaderSpec, ResponseSpec, validate
from django_modern_rest.openapi.markers import Binary
from django_modern_rest.plugins.pydantic import PydanticSerializer

_FILEPATH: Final = pathlib.Path('examples/components/receipt.txt')


@final
class FileController(Controller[PydanticSerializer]):
    @validate(
        ResponseSpec(
            Binary,
            status_code=HTTPStatus.OK,
            headers={
                'Content-Length': HeaderSpec(),
                'Content-Disposition': HeaderSpec(),
            },
        ),
    )
    def get(self) -> FileResponse:
        return FileResponse(
            _FILEPATH.open(mode='rb'),
            filename='receipt.txt',
            as_attachment=True,
            content_type='text/plain',
        )


# run: {"controller": "FileController", "method": "get", "url": "/api/file/", "curl_args": ["-D", "-"]}  # noqa: ERA001, E501
