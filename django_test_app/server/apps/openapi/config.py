from django_modern_rest.openapi import (
    OpenAPIConfig,
)
from django_modern_rest.openapi.objects import (
    Contact,
    ExternalDocumentation,
    License,
    Server,
    Tag,
)


def get_openapi_config() -> OpenAPIConfig:
    return OpenAPIConfig(
        title='Test API',
        version='1.0.0',
        summary='Test Summary',
        description='Test Description',
        terms_of_service='Test Terms of Service',
        contact=Contact(name='Test Contact', email='test@test.com'),
        license=License(name='Test License', identifier='license'),
        external_docs=ExternalDocumentation(
            url='https://test.com',
            description='Test External Documentation',
        ),
        servers=[Server(url='http://127.0.0.1:8000/api/')],
        tags=[
            Tag(name='Test Tag', description='Tag Description'),
            Tag(name='Test Tag 2', description='Tag 2 Description'),
        ],
    )
