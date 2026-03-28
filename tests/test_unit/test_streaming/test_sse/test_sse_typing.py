import sys
import typing
from collections.abc import AsyncGenerator, AsyncIterator

import pytest

from dmr.exceptions import UnsolvableAnnotationsError
from dmr.plugins.pydantic import PydanticSerializer
from dmr.streaming.sse import SSEController


@pytest.mark.parametrize(
    'annotation',
    [
        AsyncGenerator[str, None],
        AsyncIterator[int],
        typing.AsyncIterator[str],
        typing.AsyncGenerator[bytes, object],
        *(
            []
            if sys.version_info < (3, 13)
            else [
                AsyncGenerator[float],
                typing.AsyncGenerator[typing.Any],
            ]
        ),
    ],
)
def test_type_annotation(
    *,
    annotation: typing.Any,
) -> None:
    """Ensures that all correct type annotations work."""

    class _ClassBasedSSE(SSEController[PydanticSerializer]):
        async def get(self) -> annotation:  # pyright: ignore[reportInvalidTypeForm]
            raise NotImplementedError


@pytest.mark.parametrize(
    'annotation',
    [
        AsyncGenerator,
        AsyncIterator,
        typing.AsyncIterator,
        typing.AsyncGenerator,
        list[int],
        typing.Iterator,
        typing.Iterator[None],
        typing.Iterable,
        typing.Iterable[str],
        typing.Generator,
        typing.Generator[int, int, int],
        None,
        int,
        typing.Any,
        typing.Literal,
    ],
)
def test_wrong_type_annotation(
    *,
    annotation: typing.Any,
) -> None:
    """Ensures that all correct type annotations work."""
    with pytest.raises(
        UnsolvableAnnotationsError,
        match='Cannot infer streaming item',
    ):

        class _ClassBasedSSE(SSEController[PydanticSerializer]):
            async def get(self) -> annotation:  # pyright: ignore[reportInvalidTypeForm]
                raise NotImplementedError
