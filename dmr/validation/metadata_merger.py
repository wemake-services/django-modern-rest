from typing import TypeVar

from typing_extensions import Sentinel

from dmr.types import EMPTY

_LayerT = TypeVar('_LayerT')


class MetadataMerger:
    """
    Define how endpoint, controller, and settings values are resolved.

    Every configurable field of the endpoint metadata is resolved
    with a single call to one of these methods.
    All layers are passed at once, from the most specific one (endpoint)
    to the least specific one (settings), so *field_name* can be used
    to change how a specific field is resolved.

    By default, nothing is merged: the first layer with an explicit value
    wins. Override this class and set it as
    :attr:`~dmr.endpoint.Endpoint.metadata_merger_cls`
    to change this. For example, to merge ``auth`` from all layers:

    .. versionadded:: 0.16.0
    """

    __slots__ = ()

    def first_defined(
        self,
        *layers: _LayerT | Sentinel | None,
        field_name: str,
    ) -> _LayerT | Sentinel | None:
        """
        Return the first explicitly defined configuration layer.

        It is used for collections, where empty ones are not explicit.

        ``None`` is an explicit value, it disables all less specific layers.
        ``EMPTY`` and empty collections are not explicit,
        the next layer is used instead. It returns ``EMPTY``
        if no layer has an explicit value.
        """
        for layer in layers:
            if layer is None:
                return None
            if not isinstance(layer, Sentinel) and layer:
                return layer
        return EMPTY

    def first_set(
        self,
        *layers: _LayerT | Sentinel,
        field_name: str,
    ) -> _LayerT | Sentinel:
        """
        Return the first configuration layer that is not ``EMPTY``.

        Unlike :meth:`first_defined`, it is used for scalar values,
        where ``False``, ``0``, and ``None`` are real values.
        It returns ``EMPTY`` if all layers are ``EMPTY``.
        """
        for layer in layers:
            if not isinstance(layer, Sentinel):
                return layer
        return EMPTY

    def empty_to_none(
        self,
        layer: _LayerT | Sentinel,
        *,
        field_name: str,
    ) -> _LayerT | None:
        """
        Convert ``EMPTY`` to ``None`` for the resolved metadata.

        Resolved metadata does not have the "not set" state anymore,
        so ``None`` is used there for missing optional values.
        It is used for endpoint-only fields, which have a single layer.
        """
        return None if isinstance(layer, Sentinel) else layer
