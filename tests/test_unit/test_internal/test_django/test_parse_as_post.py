from django.core.files.uploadedfile import (
    SimpleUploadedFile,
    TemporaryUploadedFile,
)
from django.test import RequestFactory, override_settings
from django.test.client import encode_multipart

from dmr.internal.django import parse_as_post


@override_settings(
    DATA_UPLOAD_MAX_MEMORY_SIZE=1,
    FILE_UPLOAD_MAX_MEMORY_SIZE=1,
)
def test_parse_as_post_not_copy_data(
    rf: RequestFactory,
) -> None:
    """Ensure request body isn't copied."""
    large_content = b'x' * 2

    boundary = 'test_boundary'
    request = rf.put(
        '/whatever/',
        data=encode_multipart(
            boundary,
            {
                'file': SimpleUploadedFile('large.txt', large_content),
            },
        ),
        content_type=f'multipart/form-data; boundary={boundary}',
    )

    parse_as_post(request)

    uploaded_file = request.FILES['file']
    assert isinstance(uploaded_file, TemporaryUploadedFile)
    assert not hasattr(uploaded_file, '_file')
    assert uploaded_file.size == len(large_content)

    uploaded_file.close()
