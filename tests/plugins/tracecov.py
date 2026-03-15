from typing import Protocol
import pytest
import tracecov

_TRACECOV_MAP_KEY: pytest.StashKey[tracecov.CoverageMap] = pytest.StashKey()
_COMPACT_WIDTH: int = 80


class RegisterTracecovMap(Protocol):
    def __call__(self, map: tracecov.CoverageMap) -> None:
        """Register coverage map for summary reporting."""


@pytest.fixture(scope='session')
def register_tracecov_map(pytestconfig: pytest.Config) -> RegisterTracecovMap:
    """Append tracecov summary to terminal when a map was registered."""
    def factory(map: tracecov.CoverageMap) -> None:
        pytestconfig.stash[_TRACECOV_MAP_KEY] = map

    return factory


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter,
    exitstatus: int,
    config: pytest.Config,
) -> None:
    """
    Append tracecov coverage summary to the terminal report.

    If a coverage map was registered via ``register_tracecov_map`` fixture,
    its text report is written to the terminal at the end of the test run.
    """
    map = config.stash.get(_TRACECOV_MAP_KEY, None)

    if map is None:
        return

    report = map.generate_text_report(width=_COMPACT_WIDTH)
    terminalreporter.write_sep('=', 'tracecov summary')
    terminalreporter.write_line(report)
