from typing import Literal

import msgspec

from dmr import Controller, FileMetadata
from dmr.parsers import MultiPartParser
from dmr.plugins.msgspec import MsgspecSerializer


class _FileModel(msgspec.Struct):
    # No other content types will be allowed:
    content_type: Literal['text/plain']
    # No other filenames will be allowed:
    name: Literal['receipt.txt', 'rules.txt']


class _UploadedFiles(msgspec.Struct):
    receipt: _FileModel
    rules: _FileModel


class FileController(Controller[MsgspecSerializer]):
    parsers = (MultiPartParser(),)

    def put(
        self,
        parsed_file_metadata: FileMetadata[_UploadedFiles],
    ) -> _UploadedFiles:
        return parsed_file_metadata


# run: {"controller": "FileController", "url": "/api/users/", "method": "put", "headers": {"Content-Type": "multipart/form-data"}, "files": {"receipt": "receipt.txt", "rules": "rules.txt"}, "body": {}}  # noqa: ERA001, E501
# run: {"controller": "FileController", "url": "/api/users/", "method": "put", "headers": {"Content-Type": "multipart/form-data"}, "files": {"receipt": "wrong.json"}, "body": {}, "curl_args": ["-D", "-"], "assert-error-text": "receipt", "fail-with-body": false}  # noqa: ERA001, E501
# openapi: {"controller": "FileController", "openapi_url": "/docs/openapi.json/"}  # noqa: ERA001, E501
