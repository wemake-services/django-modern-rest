# flake8: noqa WPS111, WPS232, WPS336, WPS519


def render_event_impl(
    sep: bytes,
    encoding: str,
    data: bytes | None,
    event: str | None,
    id: int | str | None,
    retry: int | None,
    comment: str | None,
) -> bytes:
    parts = bytearray()
    chunk: bytes

    if comment is not None:
        comment_raw = comment.encode(encoding)
        start = 0
        i = 0
        length = len(comment_raw)
        while i < length:
            if comment_raw[i : i + 2] == b'\r\n':
                parts.extend(b'%s%s%s' % (b': ', comment_raw[start:i], sep))
                i += 2
                start = i
            elif (
                comment_raw[i : i + 1] == b'\r'
                or comment_raw[i : i + 1] == b'\n'
            ):
                parts.extend(b'%s%s%s' % (b': ', comment_raw[start:i], sep))
                i += 1
                start = i
            else:
                i += 1
        parts.extend(b'%s%s%s' % (b': ', comment_raw[start:], sep))

    if id is not None:
        parts.extend(b'%s%s%s' % (b'id: ', str(id).encode(encoding), sep))

    if event is not None:
        parts.extend(b'%s%s%s' % (b'event: ', event.encode(encoding), sep))

    if data is not None:
        start = 0
        i = 0
        length = len(data)
        while i < length:
            if data[i : i + 2] == b'\r\n':
                parts.extend(b'%s%s%s' % (b'data: ', data[start:i], sep))
                i += 2
                start = i
            elif data[i : i + 1] == b'\r' or data[i : i + 1] == b'\n':
                parts.extend(b'%s%s%s' % (b'data: ', data[start:i], sep))
                i += 1
                start = i
            else:
                i += 1
        parts.extend(b'%s%s%s' % (b'data: ', data[start:], sep))

    if retry is not None:
        parts.extend(
            b'%s%s%s'
            % (
                b'retry: ',
                str(retry).encode(encoding),
                sep,
            )
        )
    parts.extend(sep)

    return bytes(parts)
