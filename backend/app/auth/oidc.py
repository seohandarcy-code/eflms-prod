"""SSO(OIDC) 클라이언트 등록 — authlib 기반.

`SSO_ISSUER_URL`의 `.well-known/openid-configuration`을 자동 디스커버리한다.
client_id/secret 없이 issuer URL만 발급하는 사내 브로커 방식에도 대응한다:
authlib은 client_secret이 비면 token_endpoint_auth_method를 자동으로 "none"으로
바꾸고, client_id가 비면 ID 토큰의 aud 클레임 검증 자체를 건너뛴다.
"""
from __future__ import annotations

import logging
from pathlib import Path

from authlib.integrations.starlette_client import OAuth

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
