from typing import ClassVar, Generic, TypeVar

from typing_extensions import override

from django_modern_rest.request_parser import RequestParserMixin
from django_modern_rest.types import infer_type_args

_QueryT = TypeVar('_QueryT')


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
        if cls.__dict__.get('__is_base_type__', False):
            return
        type_args = infer_type_args(cls, BaseQuery)
        if type_args is None or len(type_args) != 1:
            raise ValueError(
                f'Type args {type_args} are not correct for {cls}, '
                'only 1 type arg must be provided',
            )
        cls.__model__ = type_args[0]
