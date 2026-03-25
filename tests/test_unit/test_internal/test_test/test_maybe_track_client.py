from typing import Any

from dmr.internal.test import maybe_track_client


def test_track_client_lookup_error() -> None:
    """Ensure tracking is skipped when fixture is missing."""

    class _PytestRequest:
        def getfixturevalue(self, name: str) -> None:
            assert name == 'tracecov_map'
            raise LookupError

    client: Any = object()
    request = _PytestRequest()

    # Should return without raising exception
    maybe_track_client(request, client)


def test_track_client_inactive_map() -> None:
    """Ensure tracking is skipped when map fixture returns ``None``."""

    class _PytestRequest:
        def getfixturevalue(self, name: str) -> None:
            assert name == 'tracecov_map'

    client: Any = object()
    request = _PytestRequest()

    # Should return without calling `track_client` or raising exception
    maybe_track_client(request, client)
