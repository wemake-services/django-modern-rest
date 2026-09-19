from dataclasses import dataclass


@dataclass(kw_only=True, slots=True)
class Discriminator:
    """
    Discriminator Object.

    When request bodies or response payloads may be one of a number of
    different schemas, a discriminator object can be used to aid in
    serialization, deserialization, and validation.
    The discriminator is a specific object in a schema which is used to
    inform the consumer of the document of an alternative schema
    based on the value associated with it.

    .. versionchanged:: 0.16.0
        Added ``default_mapping`` from OpenAPI 3.2.

    """

    property_name: str
    mapping: dict[str, str] | None = None

    # OpenAPI 3.2+ fields:
    #: Schema to use when the discriminating property is missing
    #: from the payload or holds an unmapped value.
    #: Required when the discriminating property is optional.
    default_mapping: str | None = None
