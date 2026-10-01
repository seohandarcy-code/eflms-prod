param()

$root = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\_ports.ps1"

# 창을 숨겨서(-WindowStyle Hidden) 띄우므로, 평소처럼 웹을 쓰면서 로그를 따로
# 보려면 파일로 남겨야 한다 — stdout/stderr를 합쳐서 하나의 로그 파일에 쓴다
# (uvicorn/Python logging 둘 다 보통 stderr로 나가므로 2>&1로 합침).
# 실시간으로 보려면 별도 창에서: Get-Content backend\uvicorn.log -Wait -Tail 20
Write-Host "Starting backend (uvicorn) on http://127.0.0.1:$BackendPort ... (log: backend\uvicorn.log)"
# PYTHONIOENCODING: 리다이렉트된 stdout/stderr는 콘솔이 아니라서 Python이 Windows
# 로캘 코드페이지(cp949 등)로 쓸 수 있다 — 한글 로그가 깨지는 걸 막기 위해 UTF-8로 고정.
$env:PYTHONIOENCODING = "utf-8"
# 작업 디렉터리를 backend/로 둬야 backend/.env와 상대경로 SQLite 파일(./eflms.db)을
# 올바르게 찾는다(프로젝트 루트에서 --app-dir로 띄우면 둘 다 엉뚱한 위치를 보게 됨).
Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", ".venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort > uvicorn.log 2>&1" `
    -WorkingDirectory "$root\backend" -WindowStyle Hidden

Write-Host "Starting frontend (vite dev) on http://127.0.0.1:$VitePort ... (log: frontend\vite.log)"
# 포트는 vite.config.ts가 frontend/.env의 VITE_PORT를 직접 읽어 server.port로 쓰므로
# 원래는 안 넘겨도 되지만, --strictPort로 "그 포트가 이미 쓰이고 있으면 조용히 다른
# 포트로 넘어가지 말고 에러로 실패"하게 해서 nginx 프록시 타겟과 어긋나는 걸 조기에 발견한다.
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd frontend && npm run dev -- --strictPort > vite.log 2>&1" `
    -WorkingDirectory $root -WindowStyle Hidden

Start-Sleep -Seconds 2

$nginxExe = (Get-Command nginx -ErrorAction SilentlyContinue).Source
if (-not $nginxExe) {
    $fallback = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\nginxinc.nginx_*\nginx-*\nginx.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($fallback) { $nginxExe = $fallback.FullName }
}
if (-not $nginxExe) {
    Write-Warning "nginx.exe를 찾을 수 없습니다. 새 PowerShell 세션을 열어 PATH를 갱신한 뒤 다시 시도하세요."
} else {
    New-Item -ItemType Directory -Force -Path "$root\nginx\logs" | Out-Null
    New-Item -ItemType Directory -Force -Path "$root\nginx\temp" | Out-Null

    # nginx.conf.template의 플레이스홀더를 실제 포트값으로 치환해 nginx.generated.conf
    # (런타임 산출물, .gitignore 대상)를 생성한다. 파일명을 따로 둬서 "이건 산출물"임을
    # 명확히 하고, Korean 주석이 없는 순수 설정 파일이라 Ascii로 고정해 인코딩 이슈를 피한다.
    $template = Get-Content "$root\nginx\nginx.conf.template" -Raw
    $rendered = $template.Replace('__NGINX_PORT__', "$NginxPort").Replace('__BACKEND_PORT__', "$BackendPort").Replace('__VITE_PORT__', "$VitePort")
    Set-Content -Path "$root\nginx\nginx.generated.conf" -Value $rendered -NoNewline -Encoding Ascii

    Write-Host "Starting nginx reverse proxy on http://127.0.0.1:$NginxPort ..."
    Start-Process -FilePath $nginxExe -ArgumentList "-p", "$root\nginx\", "-c", "nginx.generated.conf" -WindowStyle Hidden
}

Start-Sleep -Seconds 2
Write-Host ""
Write-Host "=== Status ==="
foreach ($port in $BackendPort, $VitePort, $NginxPort) {
    $listening = [bool](Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue)
    Write-Host "port $port : $(if ($listening) { 'UP' } else { 'DOWN' })"
}
