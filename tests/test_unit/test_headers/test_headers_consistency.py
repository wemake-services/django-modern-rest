from typing import Any

import pytest

from django_modern_rest.headers import HeaderDict


def test_case_insensitive_access() -> None:
    """Check that headers are accessible regardless of key case."""
    header_dict = HeaderDict()
    header_dict['content-type'] = 'application/json'
    assert header_dict['CoNtEnT-TyPe'] == 'application/json'
    assert header_dict['CONTENT-TYPE'] == 'application/json'
    assert header_dict['content-type'] == 'application/json'
    assert 'Content-Type' in header_dict
    assert 'content-type' in header_dict


def test_set_and_get_single_value() -> None:
    """Test setting and retrieving a single header value."""
    header_dict = HeaderDict()
    header_dict['accept'] = 'text/html'
    assert header_dict['Accept'] == 'text/html'


def test_set_sequence_of_strings() -> None:
    """Test setting a header from a list of string values."""
    header_dict = HeaderDict()
    header_dict['accept'] = ['text/html', 'application/json']
    assert header_dict['Accept'] == 'text/html,application/json'


def test_overwrite_existing_header() -> None:
    """Confirm that overwriting an existing header replaces its value."""
    header_dict = HeaderDict()
    header_dict['content-type'] = 'application/json'
    header_dict['Content-Type'] = 'text/html'
    assert header_dict['Content-Type'] == 'text/html'


def test_setting_sequence_with_mixed_types() -> None:
    """Ensure mixed-type sequences are coerced to strings and joined."""
    header_dict = HeaderDict()
    header_dict.add('x-values', ['a', '1', 'b'])
    assert header_dict['X-Values'] == 'a,1,b'


@pytest.mark.parametrize(
    'bad_header_value',
    [123, b'bytes', object, [b'', '', b'2'], [[[]]]],
)
def test_setting_bad_values_raises(
    bad_header_value: Any,
) -> None:
    """Ensure non-string and non-sequence values raise a TypeError."""
    header_dict = HeaderDict()
    with pytest.raises(TypeError):
        header_dict['x-header'] = bad_header_value


@pytest.mark.parametrize(
    'bad_header_key',
    [123, b'bytes', object, 'Set-Cookie', 'set-cookie'],
)
def test_setting_bad_keys_raises(bad_header_key: Any) -> None:
    """Check that non-string keys raise a TypeError on assignment."""
    header_dict = HeaderDict()
    with pytest.raises((TypeError, ValueError)):
        header_dict[bad_header_key] = 'abc'


def test_pop_removes_key() -> None:
    """Ensure deleting a header removes it from the dict."""
    header_dict = HeaderDict()
    header_dict['x'] = '1'
    assert 'X' in header_dict
    header_dict.pop('x')
    assert 'X' not in header_dict


def test_update_merges_same_key_values() -> None:
    """Ensure update() merges keys into a single comma-joined value."""
    h1 = HeaderDict()
    h1['accept'] = 'text/html'
    h2 = {'Accept': 'application/json'}
    h1.update(h2, accept='*')
    assert h1['Accept'] == 'text/html,application/json,*'


def test_pipe_operator_forbidden() -> None:
    """Verify that | merges keys into a single comma-joined value."""
    h1 = HeaderDict()
    h1['accept'] = 'text/html'
    h2 = HeaderDict()
    h2['ACCEPT'] = 'application/json'
    with pytest.raises(NotImplementedError):
        _ = h1 | h2  # noqa: WPS122
    with pytest.raises(NotImplementedError):
        h1 |= h2
    assert h1['accept'] == 'text/html'
