import pytest

from django_modern_rest.headers import HeaderDict


def test_make_key_normalizes_case() -> None:
    """Ensure header keys are normalized to Title-Case format."""
    assert HeaderDict._make_key('content-type') == 'Content-Type'  # noqa: SLF001
    assert HeaderDict._make_key('ACCEPT') == 'Accept'  # noqa: SLF001
    assert HeaderDict._make_key('X-Api-Key') == 'X-Api-Key'  # noqa: SLF001


def test_make_key_raises_on_non_string() -> None:
    """Verify that non-string keys raise a TypeError."""
    with pytest.raises(TypeError, match='Headers keys must be `str`'):
        HeaderDict._make_key(123)  # type: ignore[arg-type] # noqa: SLF001,WPS432


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
    header_dict['x-values'] = ['a', 1, 'b']
    assert header_dict['X-Values'] == 'a,1,b'


def test_setting_list_with_one_item() -> None:
    """Verify that a single-item list behaves the same as a single string."""
    header_dict = HeaderDict()
    header_dict['accept'] = 'text/plain'
    assert header_dict['Accept'] == 'text/plain'
    header_dict['accept'] = ['text/plain']
    assert header_dict['Accept'] == 'text/plain'


def test_setting_non_string_or_sequence_raises() -> None:
    """Ensure non-string and non-sequence values raise a TypeError."""
    header_dict = HeaderDict()
    with pytest.raises(
        TypeError,
        match=r'Headers values must be `str` or `Sequence\[str\]`',
    ):
        header_dict['x-header'] = 123


def test_setting_key_non_string_raises() -> None:
    """Check that non-string keys raise a TypeError on assignment."""
    header_dict = HeaderDict()
    with pytest.raises(TypeError, match='Headers keys must be `str`'):
        header_dict[1] = 'abc'  # type: ignore[index]


def test_len_and_iteration_behavior() -> None:
    """Verify dictionary-like length and iteration behavior."""
    header_dict = HeaderDict()
    header_dict['a'] = 'b'
    header_dict['b'] = 'c'
    assert len(header_dict) == 2
    assert sorted(header_dict.keys()) == ['A', 'B']
    assert list(header_dict.values()) == ['b', 'c']


def test_delitem_removes_key() -> None:
    """Ensure deleting a header removes it from the dict."""
    header_dict = HeaderDict()
    header_dict['x'] = '1'
    assert 'X' in header_dict
    del header_dict['x']  # noqa: WPS420
    assert 'X' not in header_dict


def test_combined_assignment_and_append_behavior() -> None:
    """Test concatenating header values using '+=' syntax."""
    header_dict = HeaderDict()
    header_dict['accept'] = 'text/html'
    # mimic appending new type
    header_dict['accept'] += ',application/json'  # noqa: WPS336
    assert header_dict['Accept'] == 'text/html,application/json'


def test_nonexistent_key_raises_keyerror() -> None:
    """Confirm accessing a missing header raises KeyError."""
    header_dict = HeaderDict()
    with pytest.raises(KeyError):
        _ = header_dict['missing']  # noqa: WPS122


def test_multiple_headers_and_iteration() -> None:
    """Ensure consistent iteration order and values across multiple headers."""
    header_dict = HeaderDict()
    header_dict['accept'] = ['text/html', 'application/json']
    header_dict['content-type'] = 'application/json'
    header_dict['cache-control'] = 'no-cache'
    keys = sorted(header_dict.keys())
    assert keys == ['Accept', 'Cache-Control', 'Content-Type']
    header_items = dict(header_dict.items())
    assert header_items['Accept'] == 'text/html,application/json'
    assert header_items['Cache-Control'] == 'no-cache'


def test_empty() -> None:
    """Ensure an empty HeaderDict behaves like an empty dict."""
    header_dict = HeaderDict()
    assert not header_dict
    assert list(header_dict.keys()) == []
    assert list(header_dict.values()) == []


@pytest.mark.skip
def test_update_merges_same_key_values() -> None:
    """Ensure update() | merges keys into a single comma-joined value."""
    h1 = HeaderDict()
    h1['accept'] = 'text/html'
    h2 = {'Accept': 'application/json'}
    h1.update(h2)
    assert h1['Accept'] == 'text/html,application/json'


@pytest.mark.skip
def test_pipe_operator_merges_same_key_values() -> None:
    """Verify that | merges keys into a single comma-joined value."""
    h1 = HeaderDict()
    h1['accept'] = 'text/html'
    h2 = HeaderDict()
    h2['ACCEPT'] = 'application/json'
    merged: HeaderDict = h1 | h2
    assert merged['Accept'] == 'text/html,application/json'
    # originals remain unchanged
    assert h1['Accept'] == 'text/html'
    assert h2['Accept'] == 'application/json'


@pytest.mark.skip
def test_inplace_pipe_operator() -> None:
    """Ensure |= merges values when both contain same header key."""
    h1 = HeaderDict()
    h1['accept'] = 'text/html'
    h2 = {'ACCEPT': 'application/json'}
    h1 |= h2
    assert h1['Accept'] == 'text/html,application/json'


@pytest.mark.skip
def test_update_with_headerdict_same_key_merges() -> None:
    """Confirm update() merges values when updating from another dict."""
    h1 = HeaderDict()
    h1['accept'] = 'text/html'
    h2 = {'accept': 'application/xml'}
    h1.update(h2)
    assert h1['Accept'] == 'text/html,application/xml'
