# certs/

사내 CA가 발급한 인증서를 쓰는 SSO 브로커(ADFS 등)에 연결할 때만 필요한 폴더다. 인증서 파일 자체는 `.gitignore` 대상이라 여기 올려둬도 커밋되지 않는다(이 README만 커밋됨).

사용법은 `docs/SECURITY_ENV.md`의 `SSO_CA_BUNDLE_PATH` 항목, 실제 겪은 문제/해결 과정은 `docs/SSO_INTEGRATION_NOTES.md` 참고.

- 이 폴더에 PEM 형식 인증서 파일을 두고(예: `internal-ca.pem`), `backend/.env`의 `SSO_CA_BUNDLE_PATH=certs/internal-ca.pem`로 상대경로를 지정한다.
- 회사에서 받은 인증서가 `.crt`/`.cer` 확장자라 DER(바이너리) 형식일 수 있다 — `openssl x509 -inform der -in <원본> -out <파일>.pem`으로 변환.
- 실제 PDEP 배포 시에는 이 폴더에 파일을 두는 대신, 인증서 내용을 K8s Secret으로 만들어 Volume mount하고 그 절대경로를 `SSO_CA_BUNDLE_PATH`로 준다(코드는 "그 경로에 파일이 있으면 읽는다"만 알면 되므로 로컬/배포 환경 분기가 없음).
