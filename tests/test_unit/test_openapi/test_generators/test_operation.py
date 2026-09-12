from typing import Final

import pytest

from dmr import Controller, modify
from dmr.openapi.config import OpenAPIConfig
from dmr.openapi.core.context import OpenAPIContext
from dmr.openapi.generators import OperationIdGenerator
from dmr.plugins.pydantic import PydanticSerializer

_TEST_CONFIG: Final = OpenAPIConfig(title='Test API', version='1.0.0')


@pytest.fixture
def generator(openapi_context: OpenAPIContext) -> OperationIdGenerator:
    """Create ``OperationIdGenerator`` instance for testing."""
    return openapi_context.generators.operation_id


@pytest.mark.parametrize(
    ('input_path', 'expected_tokens'),
    [
        # Basic paths without variables
        ('/users', ['Users']),
        ('/api/users', ['Api', 'Users']),
        ('/api/v1/users', ['Api', 'V1', 'Users']),
        ('users', ['Users']),
        ('api/users', ['Api', 'Users']),
        # Paths with path variables
        ('/users/{id}', ['Users', 'Id']),
        ('/api/users/{user_id}', ['Api', 'Users', 'UserId']),
        ('/api/{version}/users/{id}', ['Api', 'Version', 'Users', 'Id']),
        ('/users/{id}/profile', ['Users', 'Id', 'Profile']),
        (
            '/shops/{shop_id}/products/{product_id}',
            ['Shops', 'ShopId', 'Products', 'ProductId'],
        ),
        # Paths with hyphen separator (word boundary)
        ('/user-profile', ['UserProfile']),
        ('/api/user-profile', ['Api', 'UserProfile']),
        ('/user-profile/settings', ['UserProfile', 'Settings']),
        ('/api/v1/user-profile', ['Api', 'V1', 'UserProfile']),
        # Paths with underscore separator (word boundary)
        ('/user_profile', ['UserProfile']),
        ('/api/user_profile', ['Api', 'UserProfile']),
        ('/user_profile/settings', ['UserProfile', 'Settings']),
        # Paths with period separator (word boundary, RFC 3986 unreserved)
        ('/file.txt', ['FileTxt']),
        ('/api/file.name', ['Api', 'FileName']),
        ('/data.json', ['DataJson']),
        ('/api/v1/data.file', ['Api', 'V1', 'DataFile']),
        # Paths with tilde separator (word boundary, RFC 3986 unreserved)
        ('/user~name', ['UserName']),
        ('/api/user~name', ['Api', 'UserName']),
        ('/data~file', ['DataFile']),
        # Paths with multiple separators
        ('/user-profile_settings', ['UserProfileSettings']),
        ('/api/user-profile.settings', ['Api', 'UserProfileSettings']),
        ('/file-name.txt', ['FileNameTxt']),
        ('/user~name-profile', ['UserNameProfile']),
        (
            '/api/v1/user-profile.settings~data',
            ['Api', 'V1', 'UserProfileSettingsData'],
        ),
        # Edge cases
        ('/', []),
        ('//', []),
        ('/api//users', ['Api', 'Users']),
        ('/users/', ['Users']),
        ('/api/users/', ['Api', 'Users']),
        # Paths with consecutive separators
        ('/user--profile', ['UserProfile']),
        ('/user__profile', ['UserProfile']),
        ('/user..profile', ['UserProfile']),
        ('/user~~profile', ['UserProfile']),
        ('/user-_-profile', ['UserProfile']),
        # Paths with numbers
        ('/api/v1', ['Api', 'V1']),
        ('/users/123', ['Users', '123']),
        ('/api/v2/users', ['Api', 'V2', 'Users']),
        ('/file-123.txt', ['File123Txt']),
        # Complex real-world examples
        (
            '/api/v1/users/{user_id}/posts/{post_id}/comments',
            ['Api', 'V1', 'Users', 'UserId', 'Posts', 'PostId', 'Comments'],
        ),
        (
            '/api/user-profile/settings~preferences',
            ['Api', 'UserProfile', 'SettingsPreferences'],
        ),
        ('/files/data.backup.json', ['Files', 'DataBackupJson']),
        (
            '/api/v1/shops/{shop_id}/products/{product_id}/reviews',
            [
                'Api',
                'V1',
                'Shops',
                'ShopId',
                'Products',
                'ProductId',
                'Reviews',
            ],
        ),
        # Paths with only separators (should result in empty tokens)
        ('/-', []),
        ('/_.', []),
        ('/~', []),
        ('/-_~.', []),
        # Paths with reserved characters
        ('/?#!$*@%+=[]{}|/\\<>^`', []),  # noqa: WPS342
    ],
)
def test_tokenize_path(
    generator: OperationIdGenerator,
    input_path: str,
    expected_tokens: list[str],
) -> None:
    """Ensure that ``_tokenize_path`` works correctly."""
    tokens = generator._tokenize_path(input_path)
    assert tokens == expected_tokens, (
        f'Tokenization failed: '
        f'Input: {input_path!r}; '
        f'Output: {tokens!r}; '
        f'Expected: {expected_tokens!r}'
    )


class _ControllerWithOperationId(Controller[PydanticSerializer]):
    @modify(operation_id='customGetUser')
    def get(self) -> list[int]:
        raise NotImplementedError


def test_explicit_operation_id(generator: OperationIdGenerator) -> None:
    """Ensure that explicit ``operation_id`` is registered and returned."""
    controller = _ControllerWithOperationId()
    operation_id = generator(
        'whatever',
        'controller',
        metadata=controller.api_endpoints['GET'].metadata,
        serializer=PydanticSerializer,
    )
    registry = generator._context.registries.operation_id

    assert operation_id == 'customGetUser'
    assert 'customGetUser' in registry._operation_ids


class _PlainController(Controller[PydanticSerializer]):
    def get(self) -> list[int]:
        raise NotImplementedError


def test_default_operation_id_generator_unchanged(
    generator: OperationIdGenerator,
) -> None:
    """Ensure the default algorithm is used when no callback is configured."""
    assert generator._context.config.operation_id_generator is None

    controller = _PlainController()
    operation_id = generator(
        '/users',
        '',
        metadata=controller.api_endpoints['GET'].metadata,
        serializer=PydanticSerializer,
    )

    assert operation_id == 'getUsers'


def test_custom_operation_id_generator() -> None:
    """Ensure a configured ``operation_id_generator`` callback is used."""

    def custom_generator(
        path: str,
        suffix: str,
        metadata: object,
        serializer: object,
    ) -> str:
        return f'custom_{suffix}_{path}'.replace('/', '_')

    context = OpenAPIContext(
        OpenAPIConfig(
            title='Test API',
            version='1.0.0',
            operation_id_generator=custom_generator,
        ),
    )
    generator = context.generators.operation_id
    controller = _PlainController()

    operation_id = generator(
        '/users',
        'ctrl',
        metadata=controller.api_endpoints['GET'].metadata,
        serializer=PydanticSerializer,
    )

    registry = generator._context.registries.operation_id
    assert operation_id == 'custom_ctrl__users'
    assert operation_id in registry._operation_ids


def test_generator_ignored_when_explicit_id() -> None:
    """Explicit per-endpoint ``operation_id`` still wins over the callback."""
    calls: list[str] = []

    def custom_generator(
        path: str,
        suffix: str,
        metadata: object,
        serializer: object,
    ) -> str:
        calls.append(path)
        return 'shouldNotBeUsed'

    context = OpenAPIContext(
        OpenAPIConfig(
            title='Test API',
            version='1.0.0',
            operation_id_generator=custom_generator,
        ),
    )
    generator = context.generators.operation_id
    controller = _ControllerWithOperationId()

    operation_id = generator(
        'whatever',
        'controller',
        metadata=controller.api_endpoints['GET'].metadata,
        serializer=PydanticSerializer,
    )

    assert operation_id == 'customGetUser'
    assert not calls
