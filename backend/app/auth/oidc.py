"""SSO(OIDC) 클라이언트 등록 — authlib 기반.

`SSO_ISSUER_URL`의 `.well-known/openid-configuration`을 자동 디스커버리한다.
client_id/secret 없이 issuer URL만 발급하는 사내 브로커 방식에도 대응한다:
authlib은 client_secret이 비면 token_endpoint_auth_method를 자동으로 "none"으로
바꾸고, client_id가 비면 ID 토큰의 aud 클레임 검증 자체를 건너뛴다.
"""
from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings

_settings = get_settings()

SSO_BROKER_CONFIGURED = bool(_settings.sso_issuer_url)

oauth = OAuth()

if SSO_BROKER_CONFIGURED:
    oauth.register(
        name="sso",
        server_metadata_url=f"{_settings.sso_issuer_url.rstrip('/')}/.well-known/openid-configuration",
        client_id=_settings.sso_client_id or None,
        client_secret=_settings.sso_client_secret or None,
        client_kwargs={"scope": "openid profile email"},
    )
