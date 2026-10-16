param()

$root = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\_ports.ps1"
. "$PSScriptRoot\_procs.ps1"

$ports = [int[]]@($BackendPort, $VitePort, $NginxPort)

# 이미 떠 있는(또는 기동 중인) dev 서버가 있으면 중단한다 — vite는 --strictPort라 포트가 겹치면
# 로그에만 실패를 남기고 조용히 죽어서, 화면엔 예전 프로세스가 계속 보이는 혼란이 생긴다.
$busy = @(Get-ListeningPids -Ports $ports)
$running = @(Get-EflmsDevProcesses)
if ($busy.Count -gt 0 -or $running.Count -gt 0) {
    foreach ($b in $busy) {
        $name = (Get-Process -Id $b.OwningProcess -ErrorAction SilentlyContinue).ProcessName
        Write-Warning "port $($b.LocalPort) is already in use (PID $($b.OwningProcess), $name)"
    }
    foreach ($proc in $running) {
        Write-Warning "dev process already running: $($proc.Name) PID $($proc.ProcessId)"
    }
    Write-Host "Run scripts\stop-dev.ps1 first, then start again."
    exit 1
}

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
# python 경로는 절대경로로 쓴다 — stop-dev.ps1이 명령줄의 프로젝트 경로로 이 프로세스를 찾는다
# (_procs.ps1). 경로에 공백이 없다는 전제(cmd /c 따옴표 처리 회피).
$backendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "$root\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort > uvicorn.log 2>&1" `
    -WorkingDirectory "$root\backend" -WindowStyle Hidden -PassThru

Write-Host "Starting frontend (vite dev) on http://127.0.0.1:$VitePort ... (log: frontend\vite.log)"
# 포트는 vite.config.ts가 frontend/.env의 VITE_PORT를 직접 읽어 server.port로 쓰므로
# 원래는 안 넘겨도 되지만, --strictPort로 "그 포트가 이미 쓰이고 있으면 조용히 다른
# 포트로 넘어가지 말고 에러로 실패"하게 해서 nginx 프록시 타겟과 어긋나는 걸 조기에 발견한다.
# cd 대상도 절대경로로 — 명령줄에 프로젝트 경로가 남아 stop-dev.ps1이 기동 중인 vite까지 찾을 수 있다.
$frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd /d $root\frontend && npm run dev -- --strictPort > vite.log 2>&1" `
    -WorkingDirectory $root -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 2

# 기동 도중 stop-dev.ps1이 실행됐거나(또는 backend/vite가 바로 죽었으면) 여기서 멈춘다 — 그대로 nginx만
# 띄우면 앞단만 남은 반쪽 상태가 된다(2026-10-17 경합 테스트에서 실제로 nginx만 남았음).
if ($backendProc.HasExited -or $frontendProc.HasExited) {
    Write-Warning "backend or frontend exited during startup (stopped, or failed - see backend\uvicorn.log / frontend\vite.log). nginx not started."
    exit 1
}

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

# 고정 대기 대신 포트별로 LISTEN이 될 때까지 최대 30초 기다린다 — vite는 뜨는 데 몇 초 걸려
# 예전엔 실제로는 뜨는 중인데 DOWN으로 표시됐다.
$deadline = (Get-Date).AddSeconds(30)
do {
    $up = @(Get-ListeningPids -Ports $ports | ForEach-Object { [int]$_.LocalPort })
    if (($ports | Where-Object { $up -notcontains $_ }).Count -eq 0) { break }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)

Write-Host ""
Write-Host "=== Status ==="
foreach ($port in $ports) {
    Write-Host "port $port : $(if ($up -contains $port) { 'UP' } else { 'DOWN (see backend\uvicorn.log / frontend\vite.log)' })"
}
