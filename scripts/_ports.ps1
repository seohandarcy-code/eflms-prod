# 공유 포트 해석 로직 — start-dev.ps1 / stop-dev.ps1이 각각 dot-source해서 쓴다.
# 호출 전에 $root(프로젝트 루트 경로) 변수가 이미 설정돼 있어야 한다.
# 세 .env 파일이 유일한 원본이다 — frontend/vite.config.ts도 같은 파일들을 직접 읽는다.

function Read-EnvValue {
    param([string]$Path, [string]$Key, [string]$Default)
    if (Test-Path $Path) {
        $line = Get-Content $Path | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
        if ($line) {
            $value = ($line -split '=', 2)[1].Trim()
            if ($value) { return $value }
        }
    }
    return $Default
}

$BackendPort = [int](Read-EnvValue -Path "$root\backend\.env" -Key "BACKEND_PORT" -Default "8000")
$VitePort    = [int](Read-EnvValue -Path "$root\frontend\.env" -Key "VITE_PORT" -Default "5173")
$NginxPort   = [int](Read-EnvValue -Path "$root\nginx\.env" -Key "NGINX_PORT" -Default "8080")
