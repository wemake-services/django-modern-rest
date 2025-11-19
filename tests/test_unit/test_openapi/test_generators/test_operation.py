from typing import Final

import pytest

from django_modern_rest import Controller, modify
from django_modern_rest.openapi.config import OpenAPIConfig
from django_modern_rest.openapi.core.context import OpenAPIContext
from django_modern_rest.openapi.generators.operation import OperationIDGenerator
from django_modern_rest.plugins.pydantic import PydanticSerializer

_TEST_CONFIG: Final = OpenAPIConfig(title='Test API', version='1.0.0')


@pytest.fixture
def generator() -> OperationIDGenerator:
    """Create OperationIDGenerator instance for testing."""
    context = OpenAPIContext(config=_TEST_CONFIG)
    return context.operation_id_generator


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
        ('/users/{id}', ['Users']),
        ('/api/users/{user_id}', ['Api', 'Users']),
        ('/api/{version}/users/{id}', ['Api', 'Users']),
        ('/users/{id}/profile', ['Users', 'Profile']),
        ('/shops/{shop_id}/products/{product_id}', ['Shops', 'Products']),
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
            ['Api', 'V1', 'Users', 'Posts', 'Comments'],
        ),
        (
            '/api/user-profile/settings~preferences',
            ['Api', 'UserProfile', 'SettingsPreferences'],
        ),
        ('/files/data.backup.json', ['Files', 'DataBackupJson']),
        (
            '/api/v1/shops/{shop_id}/products/{product_id}/reviews',
            ['Api', 'V1', 'Shops', 'Products', 'Reviews'],
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
    generator: OperationIDGenerator,
    input_path: str,
    expected_tokens: list[str],
) -> None:
    """Test that `_tokenize_path` correctly tokenizes paths."""
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


def test_explicit_operation_id(generator: OperationIDGenerator) -> None:
    """Test that explicit operation_id is registered and returned."""
    controller = _ControllerWithOperationId()
    operation_id = generator.generate(
        controller.api_endpoints['GET'],
        path='whatever',
    )
    registry = generator.context.operation_id_registry

    assert operation_id == 'customGetUser'
    assert 'customGetUser' in registry._operation_ids
