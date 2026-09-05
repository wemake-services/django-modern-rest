import json
from typing import Any, Final, cast, final

import jwt
from typing_extensions import override

from dmr.internal.json import json_dumps_bytes, json_loads


@final
class _DMRPyJWT(jwt.PyJWT):
    """
    ``PyJWT`` that serializes the payload with our json backend.

    ``pyjwt`` hardcodes the stdlib :mod:`json` module, but exposes
    ``_encode_payload`` / ``_decode_payload`` as documented override points.
    We reuse :mod:`dmr.internal.json`, so ``msgspec`` is used when installed.

    Note that this instance owns its own ``PyJWS`` object, unlike the
    ``pyjwt`` module-level global, so globally registered custom algorithms
    are not visible here.
    """

    @override
    def _encode_payload(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
        json_encoder: type[json.JSONEncoder] | None = None,
    ) -> bytes:
        if json_encoder is not None:
            return super()._encode_payload(payload, headers, json_encoder)
        return json_dumps_bytes(payload)

    @override
    def _decode_payload(self, decoded: dict[str, Any]) -> dict[str, Any]:
        payload: Any
        try:
            payload = json_loads(decoded['payload'])
        except ValueError as exc:
            raise jwt.exceptions.DecodeError(
                f'Invalid payload string: {exc}',
            ) from exc
        if not isinstance(payload, dict):
            raise jwt.exceptions.DecodeError(
                'Invalid payload string: must be a json object',
            )
        return cast('dict[str, Any]', payload)


dmr_jwt: Final = _DMRPyJWT()
