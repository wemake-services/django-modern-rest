from typing import assert_type

from dmr.sse import SSE, SSEvent

event: SSE = SSEvent(event='test')

assert_type(SSEvent({1: 'a'}), SSEvent[dict[int, str]])
assert_type(SSEvent(b''), SSEvent[bytes])
assert_type(SSEvent(b'', serialize=False), SSEvent[bytes])
SSEvent(b'', serialize=True)
SSEvent(['a', 1], serialize=True)

# Wrong:
SSEvent([], serialize=False)  # type: ignore[call-overload]
