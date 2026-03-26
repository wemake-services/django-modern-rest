from dmr.openapi import OpenAPIConfig
from dmr.openapi.objects import (
    Contact,
    ExternalDocumentation,
    License,
)


def get_config() -> OpenAPIConfig:
    return OpenAPIConfig(
        title='Test API',
        version='1.0.0',
        summary='Test App Summary',
        description='Test App Description',
        terms_of_service='Test App Terms of Service',
        contact=Contact(name='Test Contact', email='test@test.com'),
        license=License(name='Test License', identifier='license'),
        external_docs=ExternalDocumentation(
            url='https://test.com',
            description='Test External Documentation',
        ),
    )
