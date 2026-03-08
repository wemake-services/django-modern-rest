from dmr.sse import SSEvent
from typing import assert_type

assert_type(SSEvent({1: 'a'}), SSEvent[dict[int, str]])
assert_type(SSEvent(b''), SSEvent[bytes])
SSEvent(b'', serialize=False)
SSEvent(b'', serialize=True)
SSEvent([], serialize=True)

# Wrong:
SSEvent([], serialize=False)  # type: ignore[call-overload]
