import dataclasses
from collections.abc import Callable, Iterator, Mapping
from typing import (  # noqa: WPS235
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Generic,
    TypeAlias,
    TypeVar,
    final,
    get_args,
    get_origin,
)

from typing_extensions import Format, get_original_bases, get_type_hints

from dmr.exceptions import UnsolvableAnnotationsError

if TYPE_CHECKING:
    # During type checking it is a recursive alias, so we can be sure
    # that json is always correct
    Json: TypeAlias = (
        str | int | float | bool | list['Json'] | dict[str, 'Json'] | None  # noqa: WPS221
    )
else:
    # However, in runtime this is not a recursive type for speed.
    # There might also be problems in validating a recursive type alias
    # with some serializers.
    # It will still be rendered as `{}` in OpenAPI.
    # Which means that it can be any valid json.
    Json: TypeAlias = Any
    """
    Recursive type alias for JSON data.

    What is JSON? Integers, floats, booleans, strings,
    list of them and dicts of them, which keys are always strings.

    In runtime it is always :data:`typing.Any`
    because of the parsing complexity,
    while in type checking it correctly defined.

    We don't recommend using it for anything serious,
    it is better to define real models instead.
    """


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

        >>> import pydantic
        >>> from dmr import Controller
        >>> from dmr.plugins.pydantic import PydanticSerializer

        >>> class MyController(Controller[PydanticSerializer]): ...

        >>> assert infer_type_args(MyController, Controller) == (
        ...     PydanticSerializer,
        ... )

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


class AnnotationsInferenceContext:
    """
    Annotation evaluation context.

    Use this type to change how controllers resolve
    type hints of their endpoints.

    For example, one can change this function
    to use :func:`inspect.get_annotations` function.
    Or to have some pre-defined global names.
    """

    __slots__ = ('_format', '_globalns', '_include_extras', '_localns')

    def __init__(
        self,
        *,
        globalns: dict[str, Any] | None = None,
        localns: Mapping[str, Any] | None = None,
        include_extras: bool = True,
        format: Format | None = None,  # noqa: A002
    ) -> None:
        """Create the context for the future annotations."""
        self._globalns = globalns
        self._localns = localns
        self._include_extras = include_extras
        self._format = format

    def __call__(self, endpoint_func: Callable[..., Any]) -> dict[str, Any]:
        """
        Get the annotations.

        Args:
            endpoint_func: function with return type annotation.

        Returns:
            Function's parsed and solved return type.

        Raises:
            UnsolvableAnnotationsError: when annotation can't be solved
                or when the annotation does not exist.

        """
        type_hints_params: dict[str, Any] = {
            'globalns': self._global_namespace(endpoint_func),
            'localns': self._localns,
            'include_extras': self._include_extras,
        }
        # No cover, because it is only available in 3.14+
        if self._format is not None:  # pragma: no cover
            type_hints_params['format'] = self._format

        try:
            return get_type_hints(endpoint_func, **type_hints_params)
        except Exception as exc:
            raise UnsolvableAnnotationsError(
                f'Annotations of {endpoint_func!r} cannot be solved',
            ) from exc

    def _global_namespace(
        self,
        endpoint_func: Callable[..., Any],
    ) -> dict[str, Any]:
        return self._globalns or endpoint_func.__globals__


class TypeVarInference:
    """Inferences type variables to the applied real type values."""

    __slots__ = ('_context', '_to_infer')

    _max_depth: ClassVar[int] = 15

    def __init__(
        self,
        to_infer: TypeVar,
        context: type[Any],
    ) -> None:
        """
        Prepare the inference.

        Args:
            to_infer: type var which needs to be inferred.
            context: its usage in inheritance with real type values provided.

        """
        self._to_infer = to_infer
        self._context = context

    def __call__(self) -> dict[TypeVar, Any]:
        """
        Run the inference.

        Returns:
            Mapping of type vars to its inferenced values.
            It can still be a type variable, if no real values are provided.

        """
        # We match type params by name, because they can be a bit different,
        # like `__type_params__` in >=3.12 and `TypeVar` in <=3.11.
        # This also ignore variance and stuff.
        type_map = {self._to_infer.__name__: self._to_infer}
        type_parameters = (self._to_infer,)

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
