import pytest

from dmr.openapi.mappers.schema_normalization import dump_schema
from dmr.openapi.objects import Encoding


def test_nested_encoding() -> None:
    """Ensure that 3.2 nested encodings are dumped correctly."""
    encoding = Encoding(
        content_type='multipart/mixed',
        encoding={'file': Encoding(content_type='image/png')},
    )

    assert dump_schema(encoding) == {
        'contentType': 'multipart/mixed',
        'encoding': {'file': {'contentType': 'image/png'}},
    }


def test_sequential_encoding() -> None:
    """Ensure that 3.2 positional encodings are dumped correctly."""
    encoding = Encoding(
        item_encoding=Encoding(content_type='text/plain'),
        prefix_encoding=[Encoding(content_type='image/png')],
    )

    assert dump_schema(encoding) == {
        'itemEncoding': {'contentType': 'text/plain'},
        'prefixEncoding': [{'contentType': 'image/png'}],
    }


@pytest.mark.parametrize(
    'positional_field',
    [
        {'item_encoding': Encoding()},
        {'prefix_encoding': [Encoding()]},
    ],
)
def test_encoding_by_name_and_position(
    positional_field: dict[str, object],
) -> None:
    """Ensure that encoding by name and by position cannot be mixed."""
    with pytest.raises(ValueError, match='Both `encoding` and `item_encoding`'):
        Encoding(
            encoding={'file': Encoding()},
            **positional_field,  # type: ignore[arg-type]
        )
