/// <reference types="vitest/config" />
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

const __dirname = dirname(fileURLToPath(import.meta.url))

// 아주 단순한 `KEY=value` .env 파서 — dotenv 의존성 없이, 포트 설정 하나만 읽으려고
// 정규 dotenv를 추가로 들여오지 않았다.
function readEnvValue(envPath: string, key: string): string | undefined {
  try {
    const content = readFileSync(envPath, 'utf-8')
    const line = content.split(/\r?\n/).find((l) => l.startsWith(`${key}=`))
    return line?.slice(key.length + 1).trim()
  } catch {
    return undefined
  }
}

const vitePort = Number(readEnvValue(resolve(__dirname, '.env'), 'VITE_PORT')) || 5173
// 백엔드 포트는 frontend/.env가 아니라 backend/.env를 원본으로 삼아 직접 읽는다 —
// 두 곳에 같은 값을 따로 적어두면 나중에 어긋날 수 있어서다.
const backendPort = Number(readEnvValue(resolve(__dirname, '../backend/.env'), 'BACKEND_PORT')) || 8000

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 127.0.0.1로 고정 — 이 시스템의 "localhost"가 IPv6(::1)로 풀리면 nginx의
    // proxy_pass http://127.0.0.1:<port>(IPv4 고정, nginx/nginx.conf.template 참고)가
    // 연결하지 못해 502가 나는 문제가 있었다.
    host: '127.0.0.1',
    port: vitePort,
    // API 호출을 상대경로(VITE_API_BASE_URL 비움)로 바꾼 데 대응 — vite 직접 접속에서도
    // nginx와 동일하게 /api, /healthz를 백엔드로 프록시한다.
    proxy: {
      '/api': `http://127.0.0.1:${backendPort}`,
      '/healthz': `http://127.0.0.1:${backendPort}`,
    },
  },
  test: {
    environment: 'jsdom',
  },
})
