import dataclasses
from collections.abc import Callable
from typing import Any, Final, final, get_args, get_origin, TypedDict
from typing_extensions import get_original_bases, get_type_hints

from django_modern_rest.exceptions import UnsolvableAnnotationsError
from django_modern_rest.openapi.config import OpenAPIConfig


#  TypedDict for Django Modern REST settings


class DMRSettings(TypedDict, total=False):
    """
    TypedDict defining the shape of django-modern-rest settings.
    """

    serialize: str | Callable[..., Any]
    deserialize: str | Callable[..., Any]
    openapi_config: OpenAPIConfig
    validate_responses: bool
    responses: list[Any]
    global_error_handler: str | Callable[..., Any]


@final
@dataclasses.dataclass(slots=True, frozen=True)
class Empty:
    """Special value for empty defaults."""


#: Default singleton for empty values.
EmptyObj: Final = Empty()


def infer_type_args(
    orig_cls: type[Any],
    given_type: type[Any],
) -> tuple[Any, ...]:
    """
    Return type args for the closest given type.

    .. code:: python

        class MyController(Query[MyModel]):
            ...

    Will return ``(MyModel, )`` for ``Query`` as *given_type*.
    """
    return tuple(
        arg
        for base_class in infer_bases(orig_cls, given_type)
        for arg in get_args(base_class)
    )


def infer_bases(
    orig_cls: type[Any],
    given_type: type[Any],
    *,
    use_origin: bool = True,
) -> list[Any]:
    """Infers ``__origin_bases__`` from the given type."""
    return [
        base
        for base in get_original_bases(orig_cls)
        if (
            (origin := get_origin(base) if use_origin else base)
            and is_safe_subclass(origin, given_type)
        )
    ]


def parse_return_annotation(endpoint_func: Callable[..., Any]) -> Any:
    """
    Parse function annotation and returns the return type.

    Args:
        endpoint_func: function with return type annotation.

    Raises:
        UnsolvableAnnotationsError: when annotation can't be solved
            or when the annotation does not exist.

    Returns:
        Function's parsed and solved return type.
    """
    try:
        return_annotation = get_type_hints(
            endpoint_func,
            globalns=endpoint_func.__globals__,
        ).get('return', EmptyObj)
    except (TypeError, NameError, ValueError) as exc:
        raise UnsolvableAnnotationsError(
            f'Annotations of {endpoint_func!r} cannot be solved',
        ) from exc

    if return_annotation is EmptyObj:
        raise UnsolvableAnnotationsError(
            f'Function {endpoint_func!r} is missing return type annotation',
        )
    return return_annotation


def is_safe_subclass(annotation: Any, base_class: type[Any]) -> bool:
    """Possibly unwraps subscribed class before checking for subclassing."""
    if annotation is None:
        annotation = type(None)
    try:
        return issubclass(
            get_origin(annotation) or annotation,
            base_class,
        )
    except TypeError:
        return False
