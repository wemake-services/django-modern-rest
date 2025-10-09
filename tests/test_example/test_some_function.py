import pytest

from django_modern_rest.example import some_function


@pytest.mark.parametrize(
    ('first', 'second', 'expected'),
    [
        (1, 2, 3),
        (2, 4, 6),
        (-2, -3, -5),
        (-5, 5, 0),
    ],
)
def test_some_function(first: int, second: int, expected: int) -> None:
    """Example test with parametrization."""
    assert some_function(first, second) == expected
