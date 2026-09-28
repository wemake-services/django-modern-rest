# dj-rest-auth to dmr mapping

`{client}` is `app` or `browser`, chosen when wiring allauth headless.

Paths and payloads differ. Every row below is a client-visible change.

## Endpoints

| `dj-rest-auth` | URL name | Target |
| --- | --- | --- |
| `POST /login` | `rest_login` | `POST /_allauth/{client}/v1/auth/login` |
| `POST /logout` | `rest_logout` | `DELETE /_allauth/{client}/v1/auth/session` |
| `GET`/`PUT`/`PATCH` `/user` | `rest_user_details` | your own dmr `Controller`, allauth serves no equivalent |
| `POST /password/change` | `rest_password_change` | `POST /_allauth/{client}/v1/account/password/change` |
| `POST /password/reset` | `rest_password_reset` | `POST /_allauth/{client}/v1/auth/password/request` |
| `POST /password/reset/confirm` | `rest_password_reset_confirm` | `POST /_allauth/{client}/v1/auth/password/reset` |
| `POST /registration/` | `rest_register` | `POST /_allauth/{client}/v1/auth/signup` |
| `POST /registration/verify-email/` | `rest_verify_email` | `POST /_allauth/{client}/v1/auth/email/verify` |
| `POST /registration/resend-email/` | `rest_resend_email` | `POST /_allauth/{client}/v1/auth/email/verify/resend` |
| `POST /token/verify` | `token_verify` | `VerifyTokenSyncController` / `VerifyTokenAsyncController` |
| `POST /token/refresh` | `token_refresh` | `RefreshTokenSyncController` / `RefreshTokenAsyncController` |

Only present with `USE_JWT = True`: `token/verify` and `token/refresh`
come from `simplejwt`, not from allauth. They map to dmr's own jwt
controllers, not to headless endpoints.

## MFA

`dj_rest_auth.mfa` maps onto allauth's MFA, which headless already exposes.

| `dj-rest-auth` | Target |
| --- | --- |
| `POST /mfa/verify` | `POST /_allauth/{client}/v1/auth/2fa/authenticate` |
| `POST /mfa/totp/activate` | `POST /_allauth/{client}/v1/account/authenticators/totp` |
| `POST /mfa/totp/deactivate` | `DELETE /_allauth/{client}/v1/account/authenticators/totp` |
| `GET /mfa/status` | `GET /_allauth/{client}/v1/account/authenticators` |
| `GET /mfa/recovery-codes` | `GET /_allauth/{client}/v1/account/authenticators/recovery-codes` |

Passkeys have no `dj-rest-auth` equivalent and are available at
`/_allauth/{client}/v1/account/authenticators/webauthn`.

## Social login

| `dj-rest-auth` | Target |
| --- | --- |
| `SocialLoginView` subclasses | `POST /_allauth/{client}/v1/auth/provider/token` |
| `SocialConnectView` subclasses | `POST /_allauth/{client}/v1/account/providers` |
| browser redirect flow | `POST /_allauth/browser/v1/auth/provider/redirect` |

Provider callback URLs are registered with the provider.
Changing them requires updating provider configuration.

## Auth classes

| Previous stack | dmr class |
| --- | --- |
| `rest_framework.authentication.TokenAuthentication` | `dmr.security.token.HeaderTokenSyncAuth` |
| `rest_framework.authentication.SessionAuthentication` | `dmr.security.django_session.DjangoSessionSyncAuth` |
| `rest_framework_simplejwt` `JWTAuthentication` | `dmr.security.jwt.HeaderJWTSyncAuth` |
| `dj_rest_auth.jwt_auth.JWTCookieAuthentication` | `dmr.security.jwt.CookieJWTSyncAuth` |
| allauth headless `XSessionTokenAuthentication` | `dmr.security.allauth.XSessionTokenSyncAuth` |

Every class has an async counterpart with `Async` instead of `Sync`.
Sync controllers need sync auth and async controllers need async auth.

## Settings

`REST_AUTH` keys become code, not configuration.

| `REST_AUTH` key | Where it goes |
| --- | --- |
| `USE_JWT` | selects the jwt auth classes |
| `JWT_AUTH_COOKIE` | `CookieJWTSyncAuth(cookie_name=...)` |
| `JWT_AUTH_REFRESH_COOKIE` | the cookie your refresh controller sets |
| `JWT_AUTH_REFRESH_COOKIE_PATH` | `NewCookie(path=...)` and `CookieSpec(path=...)` |
| `JWT_AUTH_HTTPONLY` | `NewCookie(httponly=...)`, keep it `True` |
| `JWT_AUTH_SECURE` | `NewCookie(secure=...)`, keep it `True` |
| `JWT_AUTH_SAMESITE` | `NewCookie(samesite=...)` |
| `JWT_AUTH_COOKIE_DOMAIN` | `NewCookie(domain=...)` |
| `JWT_AUTH_COOKIE_USE_CSRF` | dmr enforces CSRF for cookie auth automatically |
| `JWT_AUTH_RETURN_EXPIRATION` | a field on your response DTO |
| `SESSION_LOGIN` | `DjangoSessionSyncController` |
| `TOKEN_MODEL` | the dmr token app model, or a swapped custom model |
| `TOKEN_CREATOR` | override token issuing on your obtain controller |
| `OLD_PASSWORD_FIELD_ENABLED` | allauth's change-password behavior, verify it |
| `LOGOUT_ON_PASSWORD_CHANGE` | allauth session handling, verify it |
| `PASSWORD_RESET_USE_SITES_DOMAIN` | allauth site/domain configuration |
| `*_SERIALIZER` | typed DTOs plus allauth adapters for behavior |
| `REGISTER_PERMISSION_CLASSES` | auth on your own controllers, if still needed |

## Serializers

| `dj-rest-auth` serializer | Replacement |
| --- | --- |
| `LoginSerializer` | allauth login payload, plus an allauth adapter for custom rules |
| `RegisterSerializer` | allauth signup payload, plus `ACCOUNT_SIGNUP_FIELDS` and an adapter |
| `UserDetailsSerializer` | input and output `TypedDict` DTOs on your own controller |
| `PasswordChangeSerializer` | allauth change-password payload |
| `PasswordResetSerializer` | allauth password request payload |
| `PasswordResetConfirmSerializer` | allauth password reset payload |
| `JWTSerializer` | your obtain-tokens response DTO |
| `TokenSerializer` | your obtain-token response DTO |

Custom validation and side effects do not move automatically.
Re-attach them to an allauth adapter or signal, and test each one.

## Parity reminders

- Keep which flows exist and who may call them.
- Keep cookie flags and CSRF behavior.
- Keep whether the current password is required to change a password.
- Keep email verification enforcement.
- Declare every response and cookie so validation and OpenAPI stay honest.
- Run repository-native linters and tests after each flow.
