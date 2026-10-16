# 공유 프로세스 판별 로직 — start-dev.ps1 / stop-dev.ps1이 dot-source해서 쓴다.
# 호출 전에 $root(프로젝트 루트 경로)가 설정돼 있어야 한다.
#
# 포트만 보고 종료하면, 아직 포트를 잡기 전(기동 중)인 vite/uvicorn을 놓쳐 고아 프로세스가
# 남는다(2026-10-17 실제로 겪음). 그래서 "이 프로젝트 경로로 띄운 dev 프로세스"를 명령줄로도
# 찾는다. start-dev.ps1이 명령줄에 프로젝트 절대경로가 들어가게 띄우는 게 전제다.
# 다른 프로젝트의 nginx/node/python, IDE 보조 프로세스, vitest 등은 건드리지 않도록
# 이름 + 명령줄 패턴을 둘 다 맞아야만 대상으로 삼는다.

function Get-ListeningPids {
    param([int[]]$Ports)
    # LISTEN 상태만 본다 — 브라우저/nginx와의 연결이나 종료 직후 TIME_WAIT까지 세면
    # 같은 PID를 여러 번 종료하거나 "still in use"로 잘못 판정한다.
    Get-NetTCPConnection -LocalPort $Ports -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.OwningProcess -gt 0 } |
        Select-Object LocalPort, OwningProcess -Unique
}

function Get-EflmsDevProcesses {
    $rootRe = [regex]::Escape($root)
    $patterns = @(
        # backend: cmd 래퍼와 uvicorn을 띄운 python (명령줄에 backend 절대경로 + uvicorn)
        @{ Names = @("cmd.exe", "python.exe"); Pattern = "$rootRe\\backend\\.*uvicorn app\.main:app" },
        # frontend: cmd 래퍼(cd /d <root>\frontend && npm run dev)와 vite 본체(node ...\vite\bin\vite.js)
        @{ Names = @("cmd.exe"); Pattern = "$rootRe\\frontend.*npm run dev" },
        @{ Names = @("node.exe"); Pattern = "$rootRe\\frontend\\node_modules\\.*\\vite\\bin\\vite\.js" },
        # nginx: -p <root>\nginx\ 로 띄운 것만 (다른 프로젝트 nginx는 제외)
        @{ Names = @("nginx.exe"); Pattern = "-p\s+`"?$rootRe\\nginx" }
    )
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $proc = $_
        $proc.CommandLine -and ($patterns | Where-Object { $_.Names -contains $proc.Name -and $proc.CommandLine -match $_.Pattern })
    }
}

function Stop-ProcessTree {
    param([int]$ProcessId)
    # 래퍼(cmd -> npm -> node)째로 끝내야 자식이 남지 않는다.
    & taskkill.exe /T /F /PID $ProcessId 2>&1 | Out-Null
}
