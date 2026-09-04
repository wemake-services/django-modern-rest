from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    SimpleUploadedFile,
    TemporaryUploadedFile,
)
from django.test import RequestFactory
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart

from dmr.internal.django import parse_as_post


def test_parse_as_post_not_copy_data(
    rf: RequestFactory,
) -> None:
    """
    Ensure request body isn't copied.

    Django's multipart parser should stream this file through upload handlers
    and store it only as a temporary file. Keeping it as an in-memory uploaded
    file would mean the bytes were copied into another Python object.
    """
    large_content = b'x' * 2

    request = rf.put(
        '/whatever/',
        data=encode_multipart(
            BOUNDARY,
            {
                'file': SimpleUploadedFile('large.txt', large_content),
            },
        ),
        content_type=MULTIPART_CONTENT,
    )

    parse_as_post(request)

    uploaded_file = request.FILES['file']
    # The uploaded bytes must be represented by Django's temporary-file upload
    # object, not by an in-memory upload object that keeps a second byte copy.
    assert isinstance(uploaded_file, TemporaryUploadedFile)
    assert not isinstance(uploaded_file, InMemoryUploadedFile)

    assert not hasattr(uploaded_file, '_file')
    assert uploaded_file.size == len(large_content)

    uploaded_file.close()
