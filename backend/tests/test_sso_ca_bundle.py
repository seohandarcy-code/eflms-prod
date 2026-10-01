from pathlib import Path

from app.auth.oidc import _looks_like_pem
from app.core.config import Settings


def test_ca_bundle_path_none_when_unset():
    settings = Settings(sso_ca_bundle_path="")
    assert settings.sso_ca_bundle_resolved_path is None


def test_ca_bundle_relative_path_resolves_under_backend_dir():
    settings = Settings(sso_ca_bundle_path="certs/internal-ca.pem")
    resolved = settings.sso_ca_bundle_resolved_path
    assert resolved is not None
    assert resolved.is_absolute()
    assert resolved.parts[-2:] == ("certs", "internal-ca.pem")


def test_ca_bundle_absolute_path_passthrough(tmp_path):
    abs_path = tmp_path / "ca.pem"
    settings = Settings(sso_ca_bundle_path=str(abs_path))
    assert settings.sso_ca_bundle_resolved_path == abs_path


def test_looks_like_pem_true_for_pem_content(tmp_path):
    pem_file = tmp_path / "ca.pem"
    pem_file.write_text("-----BEGIN CERTIFICATE-----\nMIIB...\n-----END CERTIFICATE-----\n")
    assert _looks_like_pem(pem_file) is True


def test_looks_like_pem_false_for_binary_content(tmp_path):
    der_file = tmp_path / "ca.der"
    der_file.write_bytes(b"\x30\x82\x01\x0a\x02\x82")
    assert _looks_like_pem(der_file) is False


def test_looks_like_pem_true_when_unreadable():
    # 존재하지 않는 파일 — OSError가 나면 판단을 보류(True)하고 실제 verify 시도에서
    # 드러나게 둔다(oidc.py의 설계 의도와 동일).
    assert _looks_like_pem(Path("C:/definitely/does/not/exist.pem")) is True
