from typing import final

import pytest

from django_modern_rest import Controller, rest
from django_modern_rest.plugins.pydantic import PydanticSerializer


@final
class ValidController(Controller[PydanticSerializer]):
    @rest(return_type=str)
    def get(self) -> str:
        return 'success'

    @rest(return_type=dict)
    def post(self) -> dict:
        return {'data': 'success'}


def test_invalid_controller_raises_validation_error() -> None:
    pattern = r'Handler InvalidController\.get\(\) must be decorated with @rest'
    with pytest.raises(ValueError, match=pattern):

        @final
        class InvalidController(Controller[PydanticSerializer]):
            def get(self) -> str:
                return 'success'

            @rest(return_type=dict)
            def post(self) -> dict:
                return {'data': 'success'}


def test_mixed_invalid_controller_raises_validation_error() -> None:
    pattern = (
        r'Handler MixedInvalidController\.put\(\) must be decorated with @rest'
    )
    with pytest.raises(ValueError, match=pattern):

        @final
        class MixedInvalidController(Controller[PydanticSerializer]):
            @rest(return_type=str)
            def get(self) -> str:
                return 'success'

            def put(self) -> str:
                return 'updated'

            @rest(return_type=dict)
            def delete(self) -> dict:
                return {'deleted': True}


@final
class EmptyController(Controller[PydanticSerializer]):
    pass


def test_valid_controller_passes_validation() -> None:
    assert ValidController.existing_http_methods == {'get', 'post'}


def test_empty_controller_passes_validation() -> None:
    assert EmptyController.existing_http_methods == set()


def test_validation_only_checks_http_methods() -> None:
    @final
    class ControllerWithHelperMethods(Controller[PydanticSerializer]):
        @rest(return_type=str)
        def get(self) -> str:
            return 'success'

        def helper_method(self) -> str:
            return 'helper'

        def _private_method(self) -> str:
            return 'private'

    assert ControllerWithHelperMethods.existing_http_methods == {'get'}


def test_validation_error_includes_class_name() -> None:
    pattern = r'TestController\.post\(\) must be decorated with @rest'
    with pytest.raises(ValueError, match=pattern):

        @final
        class TestController(Controller[PydanticSerializer]):
            def post(self) -> str:
                return 'success'
