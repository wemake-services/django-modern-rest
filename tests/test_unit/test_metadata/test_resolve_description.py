import pytest

from django_modern_rest import modify
from django_modern_rest.controller import Controller
from django_modern_rest.plugins.pydantic import PydanticSerializer


class _PaylodDescriptionController(
    Controller[PydanticSerializer],
):
    @modify(
        summary='Summary from payload.',
        description='Description from payload.',
    )
    def get(self) -> list[int]:
        raise NotImplementedError


class _PaylodDocDescriptionController(
    Controller[PydanticSerializer],
):
    @modify(
        summary='Summary from payload.',
        description='Description from payload.',
    )
    def get(self) -> list[int]:
        """Summary from docstring.

        Description from docstring.
        """
        raise NotImplementedError


class _PaylodDocOnlySummaryController(
    Controller[PydanticSerializer],
):
    @modify(summary='Summary from payload.')
    def get(self) -> list[int]:
        """Summary from docstring.

        Description from docstring.
        """
        raise NotImplementedError


class _PaylodDocOnlyDescriptionController(
    Controller[PydanticSerializer],
):
    @modify(description='Description from payload.')
    def get(self) -> list[int]:
        """Summary from docstring.

        Description from docstring.
        """
        raise NotImplementedError


class _DocFullDescriptionController(
    Controller[PydanticSerializer],
):
    @modify()
    def get(self) -> list[int]:
        """Summary from docstring.

        Description from docstring.
        """
        raise NotImplementedError


class _EndpointOnlySummaryController(
    Controller[PydanticSerializer],
):
    @modify()
    def get(self) -> list[int]:
        """Only summary from docstring."""
        raise NotImplementedError


class _EmptyDescriptionController(
    Controller[PydanticSerializer],
):
    @modify()
    def get(self) -> list[int]:
        raise NotImplementedError


class _RawDescriptionController(
    Controller[PydanticSerializer],
):
    def get(self) -> list[int]:
        """Summary for raw data.

        Description for raw data.
        """
        raise NotImplementedError


@pytest.mark.parametrize(
    ('controller', 'expected_summary', 'expected_description'),
    [
        (
            _PaylodDescriptionController,
            'Summary from payload.',
            'Description from payload.',
        ),
        (
            _PaylodDocDescriptionController,
            'Summary from payload.',
            'Description from payload.',
        ),
        (
            _PaylodDocOnlySummaryController,
            'Summary from payload.',
            None,
        ),
        (
            _PaylodDocOnlyDescriptionController,
            None,
            'Description from payload.',
        ),
        (
            _DocFullDescriptionController,
            'Summary from docstring.',
            'Description from docstring.',
        ),
        (
            _EndpointOnlySummaryController,
            'Only summary from docstring.',
            None,
        ),
        (
            _EmptyDescriptionController,
            None,
            None,
        ),
        (
            _RawDescriptionController,
            'Summary for raw data.',
            'Description for raw data.',
        ),
    ],
)
def test_metadata_resolve_description(
    *,
    controller: Controller[PydanticSerializer],
    expected_summary: str | None,
    expected_description: str | None,
) -> None:
    """Ensure resolve description works correctly with/without payload."""
    endpoint = controller.api_endpoints['GET']

    assert endpoint.metadata.summary == expected_summary
    assert endpoint.metadata.description == expected_description
