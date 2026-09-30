from typing import TYPE_CHECKING, Annotated, TypeAlias, TypeVar

from typing_extensions import override

from dmr.components import BodyComponent
from dmr.exceptions import EndpointMetadataError
from dmr.plugins.msgspec.serializer import MsgspecSerializer

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.metadata import EndpointMetadata
    from dmr.serializer import BaseSerializer

_BodyT = TypeVar('_BodyT')


class BodyMsgspecComponent(BodyComponent):
    """
    Parses body of the request directly into its model with ``msgspec``.

    It is :class:`~dmr.components.BodyComponent` in fast mode,
    which only works with :class:`~dmr.plugins.msgspec.MsgspecSerializer`
    and parsers that decode into models, like
    :class:`~dmr.plugins.msgspec.MsgspecJsonParser`
    and :class:`~dmr.plugins.msgspec.MsgpackParser`.
    Use :data:`BodyMsgspec` alias, see :ref:`fast-body-component`.

    .. versionadded:: 0.16.0
    """

    __slots__ = ()

    def __init__(self) -> None:
        """Always parses bodies in fast mode."""
        super().__init__(fast_mode=True)

    @override
    def validate(
        self,
        controller_cls: type['Controller[BaseSerializer]'],
        metadata: 'EndpointMetadata',
    ) -> None:
        """
        Validate that the controller uses ``msgspec`` serializer.

        Other serializers cannot parse bodies directly into their models,
        so we raise :exc:`~dmr.exceptions.EndpointMetadataError`
        for them during the import time.
        """
        serializer = controller_cls.serializer
        if not issubclass(serializer, MsgspecSerializer):
            raise EndpointMetadataError(
                f'{metadata.endpoint_name!r} uses `BodyMsgspec`, but '
                f'{serializer.__qualname__} is not a `MsgspecSerializer`, '
                'use `Body` instead',
            )


BodyMsgspec: TypeAlias = Annotated[_BodyT, BodyMsgspecComponent()]
"""
Annotated alias for parsing requests bodies directly into ``msgspec`` models.

It is a drop-in replacement for :data:`~dmr.components.Body`
for :class:`~dmr.plugins.msgspec.MsgspecSerializer`,
which is faster, but has some limitations.
See :ref:`fast-body-component` to learn more.

.. versionadded:: 0.16.0
"""
