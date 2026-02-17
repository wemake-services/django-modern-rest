from dataclasses import dataclass
from typing import final


@final
@dataclass(unsafe_hash=True, frozen=True, kw_only=True, slots=True)
class Discriminator:
    """
    Discriminator Object.

    When request bodies or response payloads may be one of a number of
    different schemas, a discriminator object can be used to aid in
    serialization, deserialization, and validation.
    The discriminator is a specific object in a schema which is used to
    inform the consumer of the document of an alternative schema
    based on the value associated with it.
    """

    property_name: str
    mapping: dict[str, str] | None = None
