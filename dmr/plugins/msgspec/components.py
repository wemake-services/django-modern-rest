from http import HTTPStatus
from typing import TYPE_CHECKING, Annotated, Any, TypeAlias, TypeVar

from typing_extensions import TypeForm, override

from dmr.components import BodyComponent
from dmr.exceptions import EndpointMetadataError, ValidationError
from dmr.plugins.msgspec.serializer import MsgspecSerializer
from dmr.types import EMPTY

if TYPE_CHECKING:
    from dmr.controller import Controller
    from dmr.endpoint import Endpoint
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

    Use :data:`~dmr.plugins.msgspec.BodyMsgspec` alias,
    see :ref:`msgspec-body-component`.

    .. versionadded:: 0.16.0
    """

    __slots__ = ()

    def __init__(self) -> None:
        """Always parses bodies in fast mode."""
        super().__init__(pass_model=True)

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

    @override
    def provide_context_data(
        self,
        endpoint: 'Endpoint',
        controller: 'Controller[BaseSerializer]',
        *,
        field_model: TypeForm[Any],
        default: Any = EMPTY,
    ) -> Any:
        serializer = controller.serializer
        try:
            return super().provide_context_data(
                endpoint,
                controller,
                field_model=field_model,
                default=default,
            )
        except serializer.validation_error as exc:
            # Sanity check for the self validation:
            assert self.pass_model  # noqa: S101
            # Only happens in fast mode, other components
            # are not validated at all in this case:
            raise ValidationError(
                serializer.serialize_validation_error(exc),
                status_code=HTTPStatus.BAD_REQUEST,
            ) from None


BodyMsgspec: TypeAlias = Annotated[_BodyT, BodyMsgspecComponent()]
"""
Annotated alias for parsing requests bodies directly into ``msgspec`` models.

It is a drop-in replacement for :data:`~dmr.components.Body`
for :class:`~dmr.plugins.msgspec.MsgspecSerializer`,
which is faster, but has some limitations.
See :ref:`msgspec-body-component` to learn more.

.. versionadded:: 0.16.0
"""
