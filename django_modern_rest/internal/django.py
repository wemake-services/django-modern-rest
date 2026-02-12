# Some code here was adapted from Django under a BSD-3 license:
# https://github.com/django/django/blob/main/LICENSE

# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.

# Redistribution and use in source and binary forms,
# with or without modification,
# are permitted provided that the following conditions are met:

#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.

#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.

#     3. Neither the name of Django nor the names of its contributors may
#        be used to endorse or promote products derived from this software
#        without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from collections.abc import Mapping
from io import BytesIO
from typing import Any, Final, TypeAlias

from django.core.exceptions import TooManyFilesSent
from django.core.files.uploadedfile import UploadedFile
from django.http.multipartparser import MultiPartParser, MultiPartParserError
from django.http.request import HttpRequest
from django.utils.datastructures import MultiValueDict

from django_modern_rest.exceptions import RequestSerializationError


def convert_multi_value_dict(
    to_parse: 'MultiValueDict[str, Any]',
    force_list: frozenset[str],
) -> dict[str, Any]:
    """
    Convert multi value dictionary to a regular one.

    Utility function to parse django's
    :class:`django.utils.datastructures.MultiValueDict`
    into a regular :class:`dict`. To do that, we require explicit *force_list*
    parameter to return lists as dict values. Otherwise, single value is set.

    We use the last value that is sent via query,
    if there are multiple ones and only one is needed.
    """
    regular_dict: dict[str, Any] = {}
    for dict_key in to_parse:
        if dict_key in force_list:
            regular_dict[dict_key] = to_parse.getlist(dict_key)
        else:
            regular_dict[dict_key] = to_parse[dict_key]
    return regular_dict


def parse_as_post(request: HttpRequest) -> None:
    """
    Parses request, populates ``.POST`` and ``.FILES`` even for other methods.

    Is only used for several content types and several methods.
    See ``django_treat_as_post`` setting.
    """
    # This code is adapted from Django itself:
    if request.content_type == 'multipart/form-data':
        request_data = BytesIO(request.body)
        # This was introduced in django6.1:
        multipart_parser_cls = getattr(
            request,
            'multipart_parser_class',
            MultiPartParser,
        )
        try:
            post, files = multipart_parser_cls(
                request.META,
                request_data,
                request.upload_handlers,
                request.encoding,
            ).parse()
        except (MultiPartParserError, TooManyFilesSent) as exc:
            # An error occurred while parsing POST data. Since when
            # formatting the error the request handler might access
            # self.POST, set self._post and self._file to prevent
            # attempts to parse POST data again.
            request._mark_post_parse_error()  # type: ignore[attr-defined]
            raise RequestSerializationError(str(exc)) from None
        else:
            request._post = post  # type: ignore[attr-defined]
            request._files = files  # type: ignore[attr-defined]

        request._dmr_parsed_as_post = True  # type: ignore[attr-defined]
        return

    # TODO: support `application/x-www-form-urlencoded`
    raise NotImplementedError


_FileMetadata: TypeAlias = dict[str, Any]


def exctract_files_metadata(
    request_files: MultiValueDict[str, UploadedFile],
    force_list: frozenset[str],
) -> Mapping[str, _FileMetadata | list[_FileMetadata]]:
    """Extracts file metadata from ``request.FILES`` from Django."""
    metadata: dict[str, _FileMetadata | list[_FileMetadata]] = {}
    for key_name in request_files:
        if key_name in force_list:
            metadata[key_name] = _process_files_metadata(
                request_files.getlist(key_name),
            )
        else:
            metadata[key_name] = _process_files_metadata(
                request_files[key_name],  # type: ignore[arg-type]
            )
    return metadata


_FILE_ATTRS: Final = (
    'size',
    'name',
    'content_type',
    'charset',
    'content_type_extra',
)


def _process_files_metadata(
    uploaded: UploadedFile | list[UploadedFile],
) -> _FileMetadata | list[_FileMetadata]:
    if isinstance(uploaded, UploadedFile):
        return _process_file_metadata(uploaded)

    return [_process_file_metadata(single_file) for single_file in uploaded]


def _process_file_metadata(uploaded: UploadedFile) -> _FileMetadata:
    return {
        attr_name: getattr(uploaded, attr_name, None)
        for attr_name in _FILE_ATTRS
    }
