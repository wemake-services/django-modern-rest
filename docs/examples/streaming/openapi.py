from dmr.openapi import OpenAPIConfig

config = OpenAPIConfig(
    title='My awesome API with streaming',
    version='0.1.0',
    openapi_version='3.2.0',  # NOTE: required to get `itemSchema` support
)
