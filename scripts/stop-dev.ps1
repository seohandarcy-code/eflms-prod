param()

$root = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\_ports.ps1"
. "$PSScriptRoot\_procs.ps1"

# [ordered] 사전은 정수 인덱스를 "위치"로 해석하므로(포트 번호로 조회 불가) 일반 해시테이블을 쓴다.
$labels = @{ $BackendPort = "backend (uvicorn)"; $VitePort = "frontend (vite)"; $NginxPort = "nginx" }
$ports = [int[]]@($BackendPort, $VitePort, $NginxPort)

# 1) 이 프로젝트로 띄운 dev 프로세스를 명령줄로 찾아 트리째 종료 — 아직 포트를 잡기 전(기동 중)인
#    vite/uvicorn까지 잡는다. cmd 래퍼를 먼저 끝내면 그 아래 npm/node, venv python이 같이 정리된다.
$procs = @(Get-EflmsDevProcesses | Sort-Object { if ($_.Name -eq "cmd.exe") { 0 } else { 1 } })
foreach ($proc in $procs) {
    if (Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue) {
        Write-Host "Stopping $($proc.Name) (PID $($proc.ProcessId))"
        Stop-ProcessTree -ProcessId $proc.ProcessId
    }
}

# 2) 그래도 우리 포트를 LISTEN 중인 게 있으면 종료(다른 방식으로 띄운 dev 서버 등).
#    nginx 전체 종료(Get-Process nginx | Stop-Process)는 하지 않는다 — 다른 프로젝트 nginx까지 꺼졌었다.
foreach ($listener in Get-ListeningPids -Ports $ports) {
    $name = (Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue).ProcessName
    Write-Host "Stopping $($labels[[int]$listener.LocalPort]) (port $($listener.LocalPort), PID $($listener.OwningProcess), $name)"
    Stop-ProcessTree -ProcessId $listener.OwningProcess
}

# 3) 해제 확인 — 종료 직후엔 잠깐 남아 있을 수 있어 최대 10초 기다린다(LISTEN만 판정).
$deadline = (Get-Date).AddSeconds(10)
do {
    $stillListening = @(Get-ListeningPids -Ports $ports)
    $leftover = @(Get-EflmsDevProcesses)
    if ($stillListening.Count -eq 0 -and $leftover.Count -eq 0) { break }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)

Write-Host ""
Write-Host "=== Status ==="
foreach ($port in $ports) {
    $owner = $stillListening | Where-Object { $_.LocalPort -eq $port } | Select-Object -First 1
    if ($owner) {
        Write-Warning "$($labels[$port]) : port $port still in use (PID $($owner.OwningProcess))"
    } else {
        Write-Host "$($labels[$port]) : port $port released"
    }
}
foreach ($proc in $leftover) {
    Write-Warning "leftover dev process: $($proc.Name) PID $($proc.ProcessId) : $($proc.CommandLine)"
}

# taskkill이 이미 사라진 자식 때문에 남긴 종료 코드(128 등)가 새어 나가지 않게, 결과로만 판정한다.
if ($stillListening.Count -gt 0 -or $leftover.Count -gt 0) { exit 1 }
exit 0
