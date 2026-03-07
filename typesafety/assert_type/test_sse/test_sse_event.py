from dmr.sse import SSEvent

SSEvent({})
SSEvent(b'')
SSEvent(b'', serialize=False)
SSEvent(b'', serialize=True)
SSEvent([], serialize=True)

# Wrong:
SSEvent([], serialize=False)  # type: ignore[call-overload]
