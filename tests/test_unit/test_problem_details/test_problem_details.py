from http import HTTPStatus

import pytest
from inline_snapshot import snapshot

from dmr.problem_details import ProblemDetailsError


@pytest.mark.parametrize(
    'field_name',
    ['instance', 'type', 'title', 'detail', 'status'],
)
def test_problem_details_extras(*, field_name: str) -> None:
    """Ensure that `extra` cannot override fields."""
    with pytest.raises(ValueError, match='Field "extra"'):
        ProblemDetailsError(
            detail='whatever1',
            status_code=HTTPStatus.OK,
            extra={field_name: 'whatever2'},
        )


def test_problem_details_format() -> None:
    """Ensure that problem details formatting is correct."""
    assert ProblemDetailsError(
        detail='whatever1',
        status_code=HTTPStatus.OK,
    ).raw_data == snapshot({'detail': 'whatever1', 'status': 200})
    assert ProblemDetailsError(
        detail='whatever1',
        title='Title',
        status_code=HTTPStatus.OK,
        show_status=False,
    ).raw_data == snapshot({'detail': 'whatever1', 'title': 'Title'})
    assert ProblemDetailsError(
        detail='whatever1',
        instance='instance',
        status_code=HTTPStatus.OK,
        show_status=False,
        show_detail=False,
    ).raw_data == snapshot({'instance': 'instance'})
    assert ProblemDetailsError(
        'whatever1',
        status_code=HTTPStatus.OK,
        extra={'field': 1},
    ).raw_data == snapshot({'detail': 'whatever1', 'status': 200, 'field': 1})
