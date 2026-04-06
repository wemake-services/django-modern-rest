from dmr.openapi import OpenAPIConfig
from dmr.openapi.objects import (
    Contact,
    ExternalDocumentation,
    License,
)


def get_config() -> OpenAPIConfig:
    return OpenAPIConfig(
        title='Framework Demo API',
        version='1.0.0',
        summary='Demo API for framework features',
        description=(
            'Test application showcasing core functionality of the framework.'
        ),
        terms_of_service='Usage is intended for testing purposes only.',
        contact=Contact(name='Core Developer', email='mail@sobolevn.me'),
        license=License(name='MIT License', identifier='MIT'),
        external_docs=ExternalDocumentation(
            url='https://django-modern-rest.readthedocs.io/',
            description='Main documentation and guides',
        ),
    )
