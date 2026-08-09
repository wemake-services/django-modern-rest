from typing import assert_type

from dmr.openapi import load_schema
from dmr.openapi.objects import Components, PathItem

assert_type(load_schema({}, PathItem), PathItem)
assert_type(load_schema({}, Components), Components)
