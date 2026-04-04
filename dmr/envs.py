import os
from typing import Final

# Settings with env vars only
# ---------------------------

#: Cache size setting for the whole app cache system.
MAX_CACHE_SIZE: Final = int(os.environ.get('DMR_MAX_CACHE_SIZE', '256'))

#: Prefer to use compiled modules if available. True by default.
USE_COMPILED: Final = os.environ.get('DMR_USE_COMPILED', '1').strip() != '0'
