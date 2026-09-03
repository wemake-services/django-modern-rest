# These re-exports are needed as a backward-compatible solution,
# before `dmr@0.15.0`, `jwt.auth` was a module, not a package.
from dmr.security.jwt.auth.base import request_jwt as request_jwt
from dmr.security.jwt.auth.base import set_request_attrs as set_request_attrs
from dmr.security.jwt.auth.header import (
    HeaderJWTAsyncAuth as HeaderJWTAsyncAuth,
)
from dmr.security.jwt.auth.header import HeaderJWTSyncAuth as HeaderJWTSyncAuth
from dmr.security.jwt.auth.header import JWTAsyncAuth as JWTAsyncAuth
from dmr.security.jwt.auth.header import JWTSyncAuth as JWTSyncAuth
