from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dmr.test import DMRAsyncClient, DMRClient


def maybe_track_client(
    pytest_request: Any,
    client: 'DMRClient | DMRAsyncClient',
) -> None:
    """
    Connect a DMR test client to TraceCov tracking.

    If the ``tracecov_map`` fixture is available and initialized, this helper
    registers the client via ``tracecov_map.django.track_client(...)`` so all
    client interactions are included in the TraceCov report. If TraceCov is not
    installed/configured, it silently does nothing.
    """
    try:
        # Optional fixture: exists only when tracecov plugin is installed.
        tracecov_map = pytest_request.getfixturevalue('tracecov_map')
    except LookupError:
        return

    # TraceCov plugin loaded, but coverage map is intentionally inactive.
    if tracecov_map is None:
        return

    tracecov_map.django.track_client(client)
