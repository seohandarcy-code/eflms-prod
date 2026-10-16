"""SSO(OIDC) 클라이언트 등록 — authlib 기반.

`SSO_ISSUER_URL`의 `.well-known/openid-configuration`을 자동 디스커버리한다.
client_id/secret 없이 issuer URL만 발급하는 사내 브로커 방식에도 대응한다:
authlib은 client_secret이 비면 token_endpoint_auth_method를 자동으로 "none"으로
바꾸고, client_id가 비면 ID 토큰의 aud 클레임 검증 자체를 건너뛴다.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlencode

import httpx
import jwt
from authlib.integrations.starlette_client import OAuth
from jwt.algorithms import RSAAlgorithm

from app.core.config import get_settings

logger = logging.getLogger("eflms.sso")

_settings = get_settings()

SSO_BROKER_CONFIGURED = bool(_settings.sso_issuer_url)


def _looks_like_pem(path: Path) -> bool:
    """CA 번들 파일이 PEM(텍스트) 형식으로 보이는지 가볍게 확인한다.

    확실한 검증은 아니다 — 실제 유효성은 TLS 핸드셰이크 시점에 ssl 모듈이 최종
    판정한다(Python ssl은 CA 번들로 PEM만 받고 DER 바이너리는 거부함). 회사에서
    받은 인증서가 .crt/.cer 확장자라 DER일 수 있는, 흔히 겪는 실수를 기동
    시점에 조금 더 빨리 알아차리기 위한 보조 장치일 뿐이다.
    """
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return True  # 못 읽으면 판단 보류 — 실제 verify 시도에서 드러나게 둔다
    return "BEGIN CERTIFICATE" in content


oauth = OAuth()

if SSO_BROKER_CONFIGURED:
    client_kwargs: dict = {"scope": "openid profile email"}

    ca_bundle_path = _settings.sso_ca_bundle_resolved_path
    if ca_bundle_path:
        # authlib의 client_kwargs는 discovery/token/userinfo 요청에 쓰이는 httpx
        # 클라이언트 생성자에 그대로 전달된다. verify는
        # authlib.integrations.httpx_client.utils.HTTPX_CLIENT_KWARGS에 포함된
        # 공식 지원 키라, 이 세 요청 전부에 내부 CA 신뢰를 한 번에 적용할 수 있는
        # 가장 정확한 주입 지점이다.
        if ca_bundle_path.exists():
            client_kwargs["verify"] = str(ca_bundle_path)
            if not _looks_like_pem(ca_bundle_path):
                logger.warning(
                    "SSO_CA_BUNDLE_PATH(%s)가 PEM 형식이 아닌 것 같습니다"
                    "(파일 안에 '-----BEGIN CERTIFICATE-----'가 없음) — DER/바이너리"
                    " 인증서라면 `openssl x509 -inform der -in <원본> -out <파일>.pem`"
                    "으로 변환하세요. 이대로 두면 실제 SSO 로그인 시도 시 SSL 에러로"
                    " 실패할 수 있습니다.",
                    ca_bundle_path,
                )
        else:
            logger.warning("SSO_CA_BUNDLE_PATH가 설정됐지만 파일을 찾을 수 없습니다: %s", ca_bundle_path)

    oauth.register(
        name="sso",
        server_metadata_url=f"{_settings.sso_issuer_url.rstrip('/')}/.well-known/openid-configuration",
        client_id=_settings.sso_client_id or None,
        client_secret=_settings.sso_client_secret or None,
        client_kwargs=client_kwargs,
    )


# --- SSO_FLOW_MODE=implicit_form_post(기본값 아님, 명시 필요) 전용 — discovery 미지원 자체 브로커 ---
#
# 이 방식의 브로커는 discovery(.well-known/openid-configuration)를 지원하지
# 않는다. {SSO_ISSUER_URL}/oidc/form-authorize로 인가 요청을 보내면
# /sso/callback에 id_token을 POST(form_post)로 바로 돌려주고(토큰 교환
# 엔드포인트 없음), {SSO_ISSUER_URL}/oidc/jwks로 서명을 직접 검증한다. 추측으로
# response_type/response_mode/nonce/scope 같은 "이론상 표준" 파라미터를
# 추가하지 않는다 — 실제 브로커가 받는 조합이 확인되기 전까지는 최소 조합만 쓴다.


def build_broker_authorize_url(redirect_uri: str) -> str:
    """브로커 인가 URL을 조립한다 — discovery 없이 직접 만든다."""
    params = urlencode({"client_id": _settings.sso_client_id, "redirect_uri": redirect_uri})
    return f"{_settings.sso_issuer_url.rstrip('/')}/oidc/form-authorize?{params}"


def verify_broker_id_token(id_token: str) -> dict:
    """{SSO_ISSUER_URL}/oidc/jwks로 서명을 검증하고 클레임을 반환한다.

    RS256/verify_aud=False로 검증한다 — 이 방식의 브로커가 실제로 발급하는 aud
    값이 client_id와 다를 수 있다. nonce 검증은 하지 않는다 —
    build_broker_authorize_url()이 애초에 nonce를 보내지 않아 비교할 대상이
    없다. 서명 검증 실패 시 jwt.ExpiredSignatureError/jwt.InvalidTokenError를
    그대로 전파한다 — 호출부(app/api/routes/admin.py)가 "로그인 거부"로 처리한다.
    """
    jwks_url = f"{_settings.sso_issuer_url.rstrip('/')}/oidc/jwks"
    ca_bundle_path = _settings.sso_ca_bundle_resolved_path
    verify = str(ca_bundle_path) if ca_bundle_path else True
    resp = httpx.get(jwks_url, verify=verify, timeout=10.0)
    resp.raise_for_status()
    jwks = resp.json()

    # kid가 있으면 매칭해서 안전하게 간다(여러 키가 섞여 있어도 안전) — kid가
    # 없는 토큰/브로커면 첫 키로 폴백한다.
    unverified_header = jwt.get_unverified_header(id_token)
    kid = unverified_header.get("kid")
    key_dict = next((k for k in jwks["keys"] if k.get("kid") == kid), jwks["keys"][0])
    public_key = RSAAlgorithm.from_jwk(json.dumps(key_dict))

    return jwt.decode(
        id_token,
        key=public_key,
        algorithms=["RS256"],
        options={"verify_signature": True, "verify_exp": True, "verify_aud": False},
    )
