param()

$root = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\_ports.ps1"

Write-Host "Starting backend (uvicorn) on http://127.0.0.1:$BackendPort ..."
# 작업 디렉터리를 backend/로 둬야 backend/.env와 상대경로 SQLite 파일(./eflms.db)을
# 올바르게 찾는다(프로젝트 루트에서 --app-dir로 띄우면 둘 다 엉뚱한 위치를 보게 됨).
Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort" `
    -WorkingDirectory "$root\backend" -WindowStyle Hidden

Write-Host "Starting frontend (vite dev) on http://127.0.0.1:$VitePort ..."
# 포트는 CLI로 넘기지 않는다 — vite.config.ts가 frontend/.env의 VITE_PORT를 직접 읽어
# server.port로 쓰므로, 같은 원본 파일을 이 스크립트도 그대로 참조하는 셈이다.
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd frontend && npm run dev" `
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

    # nginx.conf.template의 플레이스홀더를 실제 포트값으로 치환해 nginx.conf(런타임 산출물,
    # .gitignore 대상)를 생성한다.
    $template = Get-Content "$root\nginx\nginx.conf.template" -Raw
    $rendered = $template.Replace('__NGINX_PORT__', "$NginxPort").Replace('__BACKEND_PORT__', "$BackendPort").Replace('__VITE_PORT__', "$VitePort")
    Set-Content -Path "$root\nginx\nginx.conf" -Value $rendered -NoNewline

    Write-Host "Starting nginx reverse proxy on http://127.0.0.1:$NginxPort ..."
    Start-Process -FilePath $nginxExe -ArgumentList "-p", "$root\nginx\", "-c", "nginx.conf" -WindowStyle Hidden
}

Start-Sleep -Seconds 2
Write-Host ""
Write-Host "=== Status ==="
foreach ($port in $BackendPort, $VitePort, $NginxPort) {
    $listening = [bool](Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue)
    Write-Host "port $port : $(if ($listening) { 'UP' } else { 'DOWN' })"
}
