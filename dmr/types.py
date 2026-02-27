import dataclasses
from collections.abc import Callable, Iterator
from typing import (
    Any,
    ClassVar,
    Final,
    Generic,
    TypeVar,
    final,
    get_args,
    get_origin,
)

from typing_extensions import get_original_bases, get_type_hints

from dmr.exceptions import UnsolvableAnnotationsError


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
            (origin := get_origin(base) if use_origin else base)  # noqa: WPS509
            and is_safe_subclass(origin, given_type)
        )
    ]


def parse_return_annotation(endpoint_func: Callable[..., Any]) -> Any:
    """
    Parse function annotation and returns the return type.

    Args:
        endpoint_func: function with return type annotation.

    Returns:
        Function's parsed and solved return type.

    Raises:
        UnsolvableAnnotationsError: when annotation can't be solved
            or when the annotation does not exist.
    """
    try:
        return_annotation = get_type_hints(
            endpoint_func,
            globalns=endpoint_func.__globals__,
            include_extras=True,
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


def infer_annotation(annotation: Any, context: type[Any]) -> Any:
    """Infers annotation in the class definition context."""
    if not isinstance(annotation, TypeVar):
        return annotation  # It is already inferred

    return TypeVarInference(annotation, context)()[annotation]


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


class TypeVarInference:
    """Inferences type variables to the applied real type values."""

    __slots__ = ('_context', '_to_infer')

    _max_depth: ClassVar[int] = 15

    def __init__(
        self,
        to_infer: type[Any] | TypeVar,
        context: type[Any],
    ) -> None:
        """
        Prepare the inference.

        Args:
            to_infer: class or type var which needs to be inferred.
            context: its usage in inheritance with real type values provided.

        """
        self._to_infer = to_infer
        self._context = context

    def __call__(self) -> dict[TypeVar, Any]:
        """
        Run the inference.

        Returns:
            Mapping of type vars to its inferenced valued.
            It can still be a type variable, if no real values are provided.

        """
        if isinstance(self._to_infer, TypeVar):
            type_map = {self._to_infer.__name__: self._to_infer}
            type_parameters = (self._to_infer,)
        else:
            # We match type params by name, because they can be a bit different,
            # like `__type_params__` in >=3.12 and `TypeVar` in <=3.11.
            # This also ignore variance and stuff.
            type_map = {
                type_param.__name__: type_arg
                for type_param, type_arg in zip(
                    self._to_infer.__parameters__,
                    get_args(self._to_infer),
                    strict=True,
                )
                if isinstance(type_param, TypeVar)
            }
            type_parameters = self._to_infer.__parameters__

        for base in reversed(list(self._resolve_orig_bases(self._context))):
            # We apply type params in the "reversed mro order".
            self._apply_base_type_params(base, type_map)
        return self._infer(type_map, type_parameters)

    def _resolve_orig_bases(self, typ: type[Any]) -> Iterator[type[Any]]:
        """Resolves ~full mro but with ``__orig_bases__`` instead of bases."""
        orig_bases = getattr(typ, '__orig_bases__', None)
        if orig_bases is None:
            orig_bases = getattr(get_origin(typ), '__orig_bases__', [])
        for base in orig_bases:
            if get_origin(base) is Generic:
                continue

            yield base
            yield from self._resolve_orig_bases(base)

    def _apply_base_type_params(
        self,
        base: type[Any],
        type_map: dict[str, Any],
    ) -> None:
        origin = get_origin(base)
        for type_param, type_arg in zip(
            getattr(origin, '__parameters__', []),
            get_args(base),
            strict=True,
        ):
            # TODO: this might be something else, like `TypeVarTuple`
            # or `ParamSpec`. But, they are not supported. Yet?
            assert isinstance(type_param, TypeVar), type_param  # noqa: S101

            is_needed = type_map.get(type_param.__name__)
            if is_needed:
                # TODO: most likely this will require
                # some extra work to support
                # type var defaults. Right now defaults
                # are ignored in the resolution.
                type_map.update({type_param.__name__: type_arg})
                if isinstance(type_arg, TypeVar):
                    type_map.update({type_arg.__name__: type_arg})

    def _infer(
        self,
        type_map: dict[str, Any],
        type_parameters: tuple[TypeVar, ...],
    ) -> dict[TypeVar, Any]:
        inferenced: dict[TypeVar, Any] = {}
        type_param: Any
        for type_param in type_parameters:
            orig_type_param = type_param
            iterations = 0
            while isinstance(type_param, TypeVar):
                iterations += 1
                type_param = type_map[type_param.__name__]
                if iterations >= self._max_depth:
                    raise UnsolvableAnnotationsError(
                        f'Cannot solve type annotations for {type_param!r}. '
                        f'Is definition for {self._to_infer!r} generic? '
                        'It must be concrete',
                    )
            inferenced.update({orig_type_param: type_param})
        return inferenced
