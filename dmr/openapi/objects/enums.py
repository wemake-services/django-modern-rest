import enum
from typing import final


@final
@enum.unique
class OpenAPIFormat(enum.StrEnum):
    """
    OpenAPI format.

    .. seealso::

        Spec:
        https://datatracker.ietf.org/doc/html/draft-bhutton-json-schema-validation-00#page-13

        Formats Registry:
        https://spec.openapis.org/registry/format/
    """

    DATE = 'date'
    DATE_TIME = 'date-time'
    DATE_TIME_LOCAL = 'date-time-local'
    TIME = 'time'
    TIME_LOCAL = 'time-local'
    DURATION = 'duration'
    HTTP_DATE = 'http-date'
    UNIX_TIME = 'unixtime'
    URL = 'url'
    EMAIL = 'email'
    IDN_EMAIL = 'idn-email'
    HOST_NAME = 'hostname'
    IDN_HOST_NAME = 'idn-hostname'
    IPV4 = 'ipv4'
    IPV4_CIDR = 'ipv4-cidr'
    IPV6 = 'ipv6'
    IPV6_CIDR = 'ipv6-cidr'
    URI = 'uri'
    URI_REFERENCE = 'uri-reference'
    URI_TEMPLATE = 'uri-template'
    JSON_POINTER = 'json-pointer'
    RELATIVE_JSON_POINTER = 'relative-json-pointer'
    IRI = 'iri'
    IRI_REFERENCE = 'iri-reference'
    UUID = 'uuid'
    REGEX = 'regex'
    BINARY = 'binary'
    PASSWORD = 'password'  # noqa: S105
    BASE64_URL = 'base64url'
    BYTE = 'byte'
    CHAR = 'char'
    COMMONMARK = 'commonmark'
    HTML = 'html'
    LANGUAGE = 'language'
    MEDIA_RANGE = 'media-range'
    INT8 = 'int8'
    INT16 = 'int16'
    INT32 = 'int32'
    INT64 = 'int64'
    UINT8 = 'uint8'
    UINT16 = 'uint16'
    UINT32 = 'uint32'
    UINT64 = 'uint64'
    FLOAT = 'float'
    DOUBLE = 'double'
    DOUBLE_INT = 'double-int'
    DECIMAL = 'decimal'
    DECIMAL128 = 'decimal128'
    SF_BINARY = 'sf-binary'
    SF_BOOLEAN = 'sf-boolean'
    SF_DECIMAL = 'sf-decimal'
    SF_INTEGER = 'sf-integer'
    SF_STRING = 'sf-string'
    SF_TOKEN = 'sf-token'  # noqa: S105


@final
@enum.unique
class OpenAPIType(enum.StrEnum):
    """OpenAPI types."""

    ARRAY = 'array'
    BOOLEAN = 'boolean'
    INTEGER = 'integer'
    NULL = 'null'
    NUMBER = 'number'
    OBJECT = 'object'
    STRING = 'string'
