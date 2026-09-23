import inspect
import sys
from collections.abc import Callable, Iterator, Mapping
from typing import (  # noqa: WPS235
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    TypeAlias,
    TypeVar,
    get_origin,
)

from typing_extensions import (
    Format,
    TypeIs,
    get_original_bases,
    get_type_hints,
)

from dmr.exceptions import UnsolvableAnnotationsError
from dmr.internal.type_inference import (
    resolve_type_args,
    resolve_type_var_default,
)
from dmr.internal.types import EMPTY as EMPTY
from dmr.internal.types import unwrap_type_alias

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


def safe_typevar(
    typevar_name: str,
    *,
    stacklevel: int = 1,
    globalns: dict[str, Any] | None = None,
) -> Any:
    """
    Typing utility to allow passing :class:`typing.TypeVar` safely.

    By default ``mypy`` and other type-checkers would raise a typing error
    on a code like this:

    .. code-block:: python

      >>> from typing import TypeVar
      >>> from http import HTTPStatus
      >>> from dmr import validate, ResponseSpec

      >>> _ModelT = TypeVar('_ModelT')

      >>> validate(
      ...     ResponseSpec(
      ...         # In traditional Python typing spec, it is not allowed
      ...         # to use type var in this context:
      ...         _ModelT,  # type: ignore[misc]
      ...         status_code=HTTPStatus.OK,
      ...     ),
      ... )
      <function ...>

    But, this function can help with this problem with no type errors:

    .. code-block:: python

      >>> validate(
      ...     ResponseSpec(
      ...         safe_typevar('_ModelT'),
      ...         status_code=HTTPStatus.OK,
      ...     ),
      ... )
      <function ...>

    Parameters:
        typevar_name: TypeVar name to find in the globals.
        stacklevel: Levels of function frames to get globals from.
        globalns: Explicit ``globals`` namespace.
            Has a higher priority than *stacklevel*.

    Raises:
        KeyError: If *typevar_name* is not found in *globalns*.

    .. versionadded:: 0.14.0
    """
    ns = globalns or sys._getframe(stacklevel).f_globals  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
    return ns[typevar_name]


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

    .. versionchanged:: 0.16.0

        Bases without explicit type args now contribute
        :pep:`696` type var defaults, if they have any.

    """
    return tuple(
        arg
        for base_class in infer_bases(orig_cls, given_type)
        for arg in resolve_type_args(base_class)
    )


def infer_bases(
    orig_cls: type[Any],
    given_type: type[Any],
    *,
    use_origin: bool = True,
) -> list[Any]:
    """
    Infers ``__origin_bases__`` from the given type.

    .. versionchanged:: 0.16.0

        Bases without explicit type args are now returned as well,
        because they can still provide :pep:`696` type var defaults.

    """
    return [
        base
        for base in get_original_bases(orig_cls)
        if (
            (origin := (get_origin(base) or base) if use_origin else base)  # noqa: WPS509
            and is_safe_subclass(origin, given_type)
        )
    ]


def infer_annotation(annotation: Any, context: type[Any]) -> Any:
    """Infers annotation in the class definition context."""
    if not isinstance(annotation, TypeVar):
        return annotation  # It is already inferred

    return TypeVarInference(annotation, context)()[annotation]


_TypeT = TypeVar('_TypeT')


def is_safe_subclass(
    annotation: Any,
    base_class: type[_TypeT],
) -> TypeIs[_TypeT]:
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


class AnnotationsContext:
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
        globalns: Mapping[str, Any] | None = None,
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
            Type aliases are unwrapped, so all the callers
            can work with real types and their metadata.

        Raises:
            UnsolvableAnnotationsError: when annotation can't be solved
                or when the annotation does not exist.

        """
        type_hints_params: dict[str, Any] = {
            'globalns': self._global_namespace(endpoint_func),
            'localns': self._localns,
            'include_extras': self._include_extras,
        }
        # `format` is only available in 3.14+
        if self._format is not None:  # pragma: >=3.14 cover
            type_hints_params['format'] = self._format

        try:
            type_hints = get_type_hints(endpoint_func, **type_hints_params)
        except Exception as exc:
            raise UnsolvableAnnotationsError(
                f'Annotations of {endpoint_func!r} cannot be solved',
            ) from exc

        return {
            context_name: unwrap_type_alias(annotation)
            for context_name, annotation in type_hints.items()
        }

    def _global_namespace(
        self,
        endpoint_func: Callable[..., Any],
    ) -> Mapping[str, Any]:
        if self._globalns is not None:
            return self._globalns
        return inspect.unwrap(endpoint_func).__globals__  # type: ignore[no-any-return]


class TypeVarInference:
    """
    Inferences type variables to the applied real type values.

    .. versionchanged:: 0.16.0

        :pep:`696` type var defaults are now used
        when the inheritance chain does not provide a real type value.

    """

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
        type_args = resolve_type_args(base)
        if not type_args:
            # Either a regular non-generic base
            # or a bare generic one without any type var defaults.
            return

        origin = get_origin(base) or base
        for type_param, type_arg in zip(
            getattr(origin, '__parameters__', []),
            type_args,
            strict=True,
        ):
            # TODO: this might be something else, like `TypeVarTuple`
            # or `ParamSpec`. But, they are not supported. Yet?
            assert isinstance(type_param, TypeVar), type_param  # noqa: S101

            # We record all type params, not just the ones we need right now:
            # a type arg can be a type var that this very base also provides
            # a value for. Which is what `PEP 696` defaults do.
            type_map.update({type_param.__name__: type_arg})

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
                type_param = self._resolve_type_var(type_param, type_map)
                if iterations >= self._max_depth:
                    raise UnsolvableAnnotationsError(
                        f'Cannot solve type annotations for {type_param!r}. '
                        f'Is definition for {self._to_infer!r} generic? '
                        'It must be concrete',
                    )
            inferenced.update({orig_type_param: type_param})
        return inferenced

    def _resolve_type_var(
        self,
        type_var: TypeVar,
        type_map: dict[str, Any],
    ) -> Any:
        resolved = type_map.get(type_var.__name__, type_var)
        if resolved is type_var:
            # Nothing in the inheritance chain provides a real value for it,
            # its `PEP 696` default is the last resort.
            return resolve_type_var_default(type_var)
        return resolved
