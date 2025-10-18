def normalize_key(key: str) -> str:
    """
    Convert a Python field name to an OpenAPI-compliant key.

    This function handles the conversion from Python naming conventions
    (snake_case) to OpenAPI naming conventions (camelCase) with special
    handling for reserved keywords and common patterns.

    Args:
        key: The Python field name to normalize

    Returns:
        The normalized key suitable for OpenAPI specification

    For example:

    .. code:: python
        >>> normalize_key('param_in')
        'in'
        >>> normalize_key('schema_not')
        'not'
        >>> normalize_key('external_docs')
        'externalDocs'
        >>> normalize_key('operation_id')
        'operationId'
        >>> normalize_key('ref')
        '$ref'
        >>> normalize_key('content_media_type')
        'contentMediaType'
    """
    if key == 'ref':
        return '$ref'

    if key == 'param_in':
        return 'in'

    if key.startswith('schema_'):
        key = key.split('_', maxsplit=1)[-1]

    if '_' in key:
        components = key.split('_')
        return components[0].lower() + ''.join(
            component.title() for component in components[1:]
        )

    return key
