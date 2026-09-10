import json
from http import HTTPStatus
from typing import ClassVar, Generic, TypeVar

import pydantic
from django.http import HttpResponse
from faker import Faker
from typing_extensions import override

from dmr import Body, Controller, ResponseSpec, modify, validate
from dmr.endpoint import ModifyAnyCallable, ValidateAnyCallable
from dmr.plugins.pydantic import PydanticFastSerializer
from dmr.serializer import BaseSerializer
from dmr.test import DMRRequestFactory

_SerializerT = TypeVar('_SerializerT', bound=BaseSerializer)
_OtherT = TypeVar('_OtherT')
_ExtraT = TypeVar('_ExtraT')


class _BodyModel(pydantic.BaseModel):
    user: str


_ModelT = TypeVar('_ModelT', bound=_BodyModel)


def test_lazy_modify(
    faker: Faker,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensure that lazy modify decorator works correctly."""

    class _BaseController(
        Controller[_SerializerT],
        Generic[_SerializerT, _ModelT],
    ):
        status_code: ClassVar[HTTPStatus] = HTTPStatus.OK

        @modify.lazy(
            lambda controller: modify(
                status_code=controller.status_code,  # type: ignore[attr-defined]
            ),
        )
        def post(self, parsed_body: Body[_ModelT]) -> str:
            return parsed_body.user

    assert _BaseController.is_abstract

    class OurController(
        _BaseController[PydanticFastSerializer, _BodyModel],
    ):
        """Concrete level."""

    assert not OurController.is_abstract
    assert OurController.serializer is PydanticFastSerializer
    metadata = OurController.api_endpoints['POST'].metadata
    assert OurController.status_code in metadata.responses
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == _BodyModel

    # Runtime check:
    request_data = faker.name()

    request = dmr_rf.post('/api/test', {'user': request_data})
    response = OurController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == OurController.status_code, response.content
    assert json.loads(response.content) == request_data


def test_lazy_modify_override(
    faker: Faker,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensure that lazy modify decorator works correctly."""

    class _BaseController(
        Controller[_SerializerT],
        Generic[_SerializerT, _ModelT],
    ):
        status_code: ClassVar[HTTPStatus] = HTTPStatus.OK

        @classmethod
        def lazy_spec(cls) -> ModifyAnyCallable:
            return modify(status_code=cls.status_code)  # pragma: no cover

        @modify.lazy(lazy_spec)
        def post(self, parsed_body: Body[_ModelT]) -> str:
            return parsed_body.user

    assert _BaseController.is_abstract

    class OurController(
        _BaseController[PydanticFastSerializer, _BodyModel],
    ):
        @classmethod
        @override
        def lazy_spec(cls) -> ModifyAnyCallable:
            return modify(status_code=HTTPStatus.IM_USED)

    assert not OurController.is_abstract
    assert OurController.serializer is PydanticFastSerializer
    metadata = OurController.api_endpoints['POST'].metadata
    assert HTTPStatus.IM_USED in metadata.responses
    assert HTTPStatus.OK not in metadata.responses
    assert HTTPStatus.CREATED not in metadata.responses
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == _BodyModel

    # Runtime check:
    request_data = faker.name()

    request = dmr_rf.post('/api/test', {'user': request_data})
    response = OurController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.IM_USED, response.content
    assert json.loads(response.content) == request_data


def test_lazy_validate(
    faker: Faker,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensure that lazy validate decorator works correctly."""

    class _BaseController(
        Controller[_SerializerT],
        Generic[_SerializerT, _ModelT],
    ):
        status_code: ClassVar[HTTPStatus] = HTTPStatus.OK

        @validate.lazy(
            lambda controller: validate(
                # TODO: fix this type.
                # Maybe we can improve it and also fix pyright?
                ResponseSpec(str, status_code=controller.status_code),  # type: ignore[attr-defined]
            ),
        )
        def post(self, parsed_body: Body[_ModelT]) -> HttpResponse:
            return self.to_response(
                parsed_body.user,
                status_code=self.status_code,
            )

    assert _BaseController.is_abstract

    class OurController(
        _BaseController[PydanticFastSerializer, _BodyModel],
    ):
        """Concrete level."""

    assert not OurController.is_abstract
    assert OurController.serializer is PydanticFastSerializer
    metadata = OurController.api_endpoints['POST'].metadata
    assert OurController.status_code in metadata.responses
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == _BodyModel

    # Runtime check:
    request_data = faker.name()

    request = dmr_rf.post('/api/test', {'user': request_data})
    response = OurController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == OurController.status_code, response.content
    assert json.loads(response.content) == request_data


def test_lazy_validate_override(
    faker: Faker,
    dmr_rf: DMRRequestFactory,
) -> None:
    """Ensure that lazy validate override decorator works correctly."""

    class _BaseController(
        Controller[_SerializerT],
        Generic[_SerializerT, _ModelT],
    ):
        status_code: ClassVar[HTTPStatus] = HTTPStatus.OK

        @classmethod
        def lazy_spec(cls) -> ValidateAnyCallable:
            return validate(ResponseSpec(str, status_code=cls.status_code))  # pragma: no cover

        @validate.lazy(lazy_spec)
        def post(self, parsed_body: Body[_ModelT]) -> HttpResponse:
            return self.to_response(
                parsed_body.user,
                status_code=self.status_code,
            )

    assert _BaseController.is_abstract

    class OurController(
        _BaseController[PydanticFastSerializer, _BodyModel],
    ):
        status_code: ClassVar[HTTPStatus] = HTTPStatus.IM_USED

        @classmethod
        @override
        def lazy_spec(cls) -> ValidateAnyCallable:
            return validate(
                ResponseSpec(str, status_code=cls.status_code),
                tags=['custom'],
            )

    assert not OurController.is_abstract
    assert OurController.serializer is PydanticFastSerializer
    metadata = OurController.api_endpoints['POST'].metadata
    assert HTTPStatus.IM_USED in metadata.responses
    assert HTTPStatus.OK not in metadata.responses
    assert HTTPStatus.CREATED not in metadata.responses
    assert len(metadata.component_parsers) == 1
    assert metadata.component_parsers[0][1] == _BodyModel
    assert metadata.tags == ['custom']

    # Runtime check:
    request_data = faker.name()

    request = dmr_rf.post('/api/test', {'user': request_data})
    response = OurController.as_view()(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == HTTPStatus.IM_USED, response.content
    assert json.loads(response.content) == request_data
