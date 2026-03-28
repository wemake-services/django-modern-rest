from typing import assert_type

from dmr.streaming.sse import SSE, SSEvent

# Correct:
event: SSE = SSEvent(event='test')

assert_type(SSEvent({1: 'a'}), SSEvent[dict[int, str]])
assert_type(SSEvent(b''), SSEvent[bytes])
assert_type(SSEvent(b'', serialize=False), SSEvent[bytes])

SSEvent(b'', serialize=True)
SSEvent(['a', 1], serialize=True)
SSEvent(event='test')
SSEvent(comment='ping')
SSEvent(id=1)
SSEvent(retry=1)

# Wrong:
SSEvent([], serialize=False)  # type: ignore[call-overload]
SSEvent()  # type: ignore[call-overload]
