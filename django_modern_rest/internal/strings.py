import sys
from functools import lru_cache

from django_modern_rest.settings import MAX_CACHE_SIZE


@lru_cache(maxsize=MAX_CACHE_SIZE)
def str_title_cached_interned(input_str: str) -> str:
    """
    Call str.title() and cache interned result.

    Used for handling header keys.
    """
    if not input_str.istitle():
        input_str = input_str.title()
    return sys.intern(input_str)
