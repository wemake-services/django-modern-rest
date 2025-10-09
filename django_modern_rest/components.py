from typing import Any, ClassVar, Generic, TypeVar

from typing_extensions import override

from django_modern_rest.request_parser import RequestParserMixin
from django_modern_rest.types import infer_type_args

_QueryT = TypeVar('_QueryT')
_BodyT = TypeVar('_BodyT')
_HeadersT = TypeVar('_HeadersT')


class BaseQuery(RequestParserMixin[_QueryT], Generic[_QueryT]):
    """
    Base type for query parsing from http requests.

    Do not use directly, use specialized version from plugins.
    """

    __is_base_type__: ClassVar[bool] = True

    parsed_query: _QueryT

    @override
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        _maybe_set_model_type(cls, BaseQuery)


class BaseBody(RequestParserMixin[_BodyT], Generic[_BodyT]):
    """
    Base type for request body parsing.

    Do not use directly, use specialized version from plugins.
    """

    __is_base_type__: ClassVar[bool] = True

    parsed_body: _BodyT

    @override
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        _maybe_set_model_type(cls, BaseBody)


class BaseHeaders(RequestParserMixin[_HeadersT], Generic[_HeadersT]):
    """
    Base type for request headers parsing.

    Do not use directly, use specialized version from plugins.
    """

    __is_base_type__: ClassVar[bool] = True

    parsed_headers: _HeadersT

    @override
    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        _maybe_set_model_type(cls, BaseHeaders)


def _maybe_set_model_type(
    orig_cls: type[Any],
    base: type[Any],
) -> None:
    if orig_cls.__dict__.get('__is_base_type__', False):
        return
    type_args = infer_type_args(orig_cls, base)
    if type_args is None or len(type_args) != 1:
        raise ValueError(
            f'Type args {type_args} are not correct for {orig_cls}, '
            'only 1 type arg must be provided',
        )
    orig_cls.__model__ = type_args[0]
