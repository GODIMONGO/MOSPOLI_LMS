param(
  [ValidateSet("install", "doctor", "configure", "open", "push", "pull", "open-github")]
  [string]$Action = "open",

  [string]$Notebook = "deploy/colab/MOSPOLI_LMS_Colab.ipynb",
  [string]$ClientSecrets = "",
  [int]$AuthUser = -1,
  [string]$RepoUrl = "",
  [string]$VenvPath = ".colab-cli-venv"
)

$ErrorActionPreference = "Stop"

function Invoke-Step($Message) {
  Write-Host "==> $Message"
}

function Test-Command($Name) {
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-RepoRoot {
  $root = git rev-parse --show-toplevel 2>$null
  if (-not $root) {
    throw "Run this command inside the MOSPOLI_LMS git repository."
  }
  return $root.Trim()
}

function Ensure-ColabCli {
  param([string]$Root)

  $python = Join-Path $Root "$VenvPath\Scripts\python.exe"
  $cli = Join-Path $Root "$VenvPath\Scripts\colab-cli.exe"

  if (-not (Test-Path $python)) {
    Invoke-Step "Creating isolated Python venv for Google Colab CLI"
    python -m venv (Join-Path $Root $VenvPath)
  }

  if (-not (Test-Path $cli)) {
    Invoke-Step "Installing PyPI colab-cli in the isolated venv"
    & $python -m pip install colab-cli GitPython
  }

  return $cli
}

function Configure-ColabCli {
  param(
    [string]$Cli,
    [string]$Root
  )

  $configDir = Join-Path $env:APPDATA "colab-cli"
  New-Item -ItemType Directory -Force -Path $configDir | Out-Null

  if ($ClientSecrets) {
    $resolvedSecrets = Resolve-Path -LiteralPath $ClientSecrets
    Invoke-Step "Configuring Google Drive OAuth client"
    & $Cli set-config $resolvedSecrets.Path
  }

  if ($AuthUser -ge 0) {
    Invoke-Step "Setting Google auth user index to $AuthUser"
    & $Cli set-auth-user $AuthUser
  }
}

function Get-DefaultRepoUrl {
  $remote = git config --get remote.origin.url 2>$null
  if ($remote) {
    return $remote.Trim()
  }
  return ""
}

function New-PreparedNotebook {
  param(
    [string]$Root,
    [string]$SourceNotebook
  )

  $sourcePath = Resolve-Path -LiteralPath (Join-Path $Root $SourceNotebook)
  $effectiveRepoUrl = $RepoUrl
  if (-not $effectiveRepoUrl) {
    $effectiveRepoUrl = Get-DefaultRepoUrl
  }

  if (-not $effectiveRepoUrl) {
    Write-Warning "Repo URL is unknown. Pass -RepoUrl or configure git remote origin before opening the notebook."
    return $sourcePath.Path
  }

  $outputDir = Join-Path $Root ".colab"
  New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
  $outputPath = Join-Path $outputDir "MOSPOLI_LMS_Colab.generated.ipynb"
  $content = Get-Content -Raw -LiteralPath $sourcePath.Path
  $content = $content.Replace("<YOUR_REPO_URL>", $effectiveRepoUrl)
  Set-Content -LiteralPath $outputPath -Value $content -Encoding UTF8
  return $outputPath
}

$root = Get-RepoRoot
Set-Location $root

$cli = Ensure-ColabCli -Root $root

switch ($Action) {
  "install" {
    Invoke-Step "Google Colab CLI is installed"
    & $cli --help
  }
  "doctor" {
    Invoke-Step "Checking Google Colab CLI"
    & $cli --help
    Invoke-Step "Checking notebook"
    Resolve-Path -LiteralPath (Join-Path $root $Notebook)
    if (Test-Command "colab") {
      Invoke-Step "Optional npm colab command is present"
      colab --version
    } else {
      Write-Host "Optional npm colab command is not installed; this wrapper uses PyPI colab-cli."
    }
  }
  "configure" {
    Configure-ColabCli -Cli $cli -Root $root
  }
  "open" {
    Configure-ColabCli -Cli $cli -Root $root
    $preparedNotebook = New-PreparedNotebook -Root $root -SourceNotebook $Notebook
    Invoke-Step "Opening notebook in Google Colab via colab-cli"
    & $cli open-nb $preparedNotebook
  }
  "push" {
    Configure-ColabCli -Cli $cli -Root $root
    $preparedNotebook = New-PreparedNotebook -Root $root -SourceNotebook $Notebook
    Invoke-Step "Pushing notebook to Google Drive via colab-cli"
    & $cli push-nb $preparedNotebook
  }
  "pull" {
    Configure-ColabCli -Cli $cli -Root $root
    Invoke-Step "Pulling notebook from Google Drive via colab-cli"
    & $cli pull-nb $Notebook
  }
  "open-github" {
    $effectiveRepoUrl = $RepoUrl
    if (-not $effectiveRepoUrl) {
      $effectiveRepoUrl = Get-DefaultRepoUrl
    }
    if (-not $effectiveRepoUrl) {
      throw "Repo URL is unknown. Pass -RepoUrl."
    }

    $repoPath = $effectiveRepoUrl -replace '^https://github.com/', '' -replace '\.git$', ''
    $branch = git branch --show-current
    if (-not $branch) {
      $branch = "main"
    }
    $notebookPath = $Notebook.Replace("\", "/")
    $url = "https://colab.research.google.com/github/$repoPath/blob/$branch/$notebookPath"
    Invoke-Step "Opening GitHub notebook in Google Colab"
    Write-Host $url
    Start-Process $url
  }
}

# Быстрый запуск MOSPOLI LMS в Google Colab

Этот сценарий не требует Docker, QEMU, VPN, Cloudflare или localtunnel. Сначала запускается быстрый mock-режим AI-навигации, чтобы проверить, что сайт и API вообще работают в Colab. Реальная GGUF-модель запускается отдельно после этого.

## 1. Открой notebook

Открой файл:

```text
deploy/colab/MOSPOLI_LMS_Colab.ipynb
```

Если открываешь через GitHub, ссылка должна вести на актуальный репозиторий/ветку после push изменений.

## 2. Выполни ячейки сверху вниз

В notebook есть готовые ячейки:

```text
1. Clone or update the project
2. Install Node.js 22 and build tools
3. Fast reliable start: frontend + API with mock embeddings
4. Local checks inside Colab
5. Open the site through Colab's built-in authenticated proxy
```

После ячейки 3 должны быть строки:

```text
Services are running.
ai-navigation-service: http://127.0.0.1:3001
frontend:              http://127.0.0.1:5173
```

## 3. Открой сайт

Запусти ячейку 5. Она использует встроенный прокси Colab:

```text
google.colab.kernel.proxyPort(5173)
```

Это не внешний tunnel. VPN обычно не мешает этому способу.

## 4. Если порт 5173 не поднялся

Запусти диагностическую ячейку 7 в notebook. Важны три вывода:

```text
ss -ltnp
.colab/logs/frontend.log
.colab/logs/ai-navigation-service.log
```

Если `frontend.log` пустой или там ошибка `Cannot find module`, значит ячейка установки зависимостей не прошла или была прервана.

Если в выводе нет `node deploy/colab/serve-frontend.mjs`, frontend-сервер не запущен.

Если `node --version` ниже `v20.19.0`, значит Node.js не обновился. Перезапусти ячейку установки Node.js.

## 5. Реальная модель Qwen/llama.cpp

Только после того как mock-режим открыл сайт, можно запускать ячейку 6:

```text
Optional: real embeddings with Qwen GGUF + llama.cpp CUDA
```

Перед этим в Colab включи GPU:

```text
Runtime -> Change runtime type -> T4 GPU
```

Реальный режим скачивает большую GGUF-модель и собирает `llama.cpp`, поэтому он может занимать много времени. Для проверки интерфейса он не нужен.

## 6. Что именно запускается

В mock-режиме:

```text
browser
  -> Colab proxy
  -> frontend static/proxy server :5173
  -> /api proxy
  -> ai-navigation-service :3001
  -> mock embeddings
```

В real-режиме:

```text
browser
  -> Colab proxy
  -> frontend static/proxy server :5173
  -> /api proxy
  -> ai-navigation-service :3001
  -> llama.cpp :8080
  -> Qwen3 GGUF
```

# Google Colab Browser Demo

Русский короткий запуск: `deploy/colab/QUICKSTART_RU.md`.

This folder runs MOSPOLI LMS in Google Colab without Docker or QEMU. The default notebook path starts mock embeddings first, so the browser UI and same-origin proxy can be verified before downloading the large GGUF model.

```text
browser URL
  -> Colab built-in proxy
  -> frontend static/proxy server :5173
  -> same-origin /api proxy
  -> ai-navigation-service :3001
  -> mock embeddings or llama.cpp embedding server :8080
```

The frontend keeps using same-origin `/api/navigation-search`. The small Node server in `serve-frontend.mjs` serves `dist/` and proxies `/api/*` to `ai-navigation-service`, because `vite preview` is not a production proxy.

## Colab cells

### 1. Enable GPU and clone the repo

In Colab: `Runtime` -> `Change runtime type` -> `T4 GPU` or better.

```python
# Clone or update the project. Replace REPO_URL if you run a fork.
REPO_URL = "https://github.com/GODIMONGO/MOSPOLI_LMS"
!test -d /content/MOSPOLI_LMS/.git && git -C /content/MOSPOLI_LMS pull --ff-only || git clone "$REPO_URL" /content/MOSPOLI_LMS
%cd /content/MOSPOLI_LMS
```

### 2. Install system packages and Node.js

```python
# Install build tools for llama.cpp and Node.js 22 for Vite/TypeScript.
!apt-get update -y
!apt-get install -y git wget curl ca-certificates cmake build-essential
!curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
!apt-get install -y nodejs
!node --version
!npm --version
```

### 3. Run the services in reliable mock mode

```python
# Starts frontend + API on 5173/3001. No model download, no llama.cpp build.
!chmod +x deploy/colab/start-colab.sh
!EMBEDDING_MOCK=true ALLOW_EMBEDDING_FALLBACK=true START_TUNNEL=none deploy/colab/start-colab.sh
```

This cell returns after the local services are running. If `curl http://127.0.0.1:5173` is refused, the startup failed before the frontend server was launched; inspect `.colab/logs/*.log`.

### 4. Smoke test

```python
# Run after the services are started.
%cd /content/MOSPOLI_LMS
!curl -fsS http://127.0.0.1:5173/
!curl -fsS http://127.0.0.1:3001/health
!AI_NAVIGATION_URL=http://127.0.0.1:3001 node ai-navigation-service/scripts/test-api.mjs
!curl -fsS -X POST http://127.0.0.1:5173/api/navigation-search \
  -H 'Content-Type: application/json' \
  -d '{"query":"регистрация","locale":"ru"}'
```

### 5. Open it in the browser with Cloudflare Tunnel

```python
# Prefer Colab's built-in proxy. It avoids Cloudflare/localtunnel and VPN issues.
from google.colab import output
from google.colab.output import eval_js

url = eval_js("google.colab.kernel.proxyPort(5173)")
print(url)
output.serve_kernel_port_as_window(5173)
```

### 6. Optional real embeddings with Qwen GGUF + llama.cpp

```python
# Use after mock mode works. Runtime -> Change runtime type -> T4 GPU or better.
%cd /content/MOSPOLI_LMS
!nvidia-smi
!EMBEDDING_MOCK=false START_TUNNEL=none deploy/colab/start-colab.sh
```

### 7. Diagnostics

```python
%cd /content/MOSPOLI_LMS
!ps -ef | grep -E 'llama-server|ai-navigation-service/dist/server.js|deploy/colab/serve-frontend.mjs' | grep -v grep || true
!ss -ltnp | grep -E ':(8080|3001|5173)\b' || true
!tail -n 80 .colab/logs/frontend.log || true
!tail -n 80 .colab/logs/ai-navigation-service.log || true
!tail -n 80 .colab/logs/llama-server.log || true
```

### 8. Optional external tunnel

```python
# Use only if Colab proxy is not enough.
%cd /content/MOSPOLI_LMS
!wget -q -O /tmp/cloudflared-linux-amd64.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
!dpkg -i /tmp/cloudflared-linux-amd64.deb
!cloudflared tunnel --url http://127.0.0.1:5173
```

## Important environment variables

```env
REPO_DIR=/content/MOSPOLI_LMS
MODEL_DIR=/content/MOSPOLI_LMS/models
MODEL_FILE=qwen3-embedding-4b-q5_k_m.gguf
MODEL_URL=https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF/resolve/main/Qwen3-Embedding-4B-Q5_K_M.gguf?download=true
LLAMA_DIR=/content/llama.cpp
LLAMA_PORT=8080
AI_PORT=3001
FRONTEND_PORT=5173
START_TUNNEL=none
```

Use `EMBEDDING_MOCK=true ALLOW_EMBEDDING_FALLBACK=true` only for a fast UI check without real embeddings.

## Open with Google Colab CLI

There are two different `colab-cli` packages:

- npm `colab-cli` exposes the `colab` command, but it only has `aws` and `redis` commands.
- PyPI `colab-cli` exposes the `colab-cli` command and can upload/open notebooks in Google Colab through Google Drive.

Use the project wrapper so the Python CLI stays isolated in `.colab-cli-venv/`:

```powershell
.\deploy\colab\colab-cli.ps1 -Action install
.\deploy\colab\colab-cli.ps1 -Action doctor
```

To let the CLI upload/open the notebook, create a Google Drive API OAuth client, download it as `client_secrets.json`, and run:

```powershell
.\deploy\colab\colab-cli.ps1 -Action configure -ClientSecrets .\client_secrets.json -AuthUser 0
.\deploy\colab\colab-cli.ps1 -Action open -RepoUrl https://github.com/<OWNER>/<REPO>.git
```

`-Action open` generates `.colab/MOSPOLI_LMS_Colab.generated.ipynb` with the repo URL inserted, uploads/opens it through `colab-cli open-nb`, and leaves runtime logs and generated files under ignored local paths.

Without Google Drive OAuth, use the GitHub-backed Colab URL after the notebook is pushed to GitHub:

```powershell
.\deploy\colab\colab-cli.ps1 -Action open-github -RepoUrl https://github.com/GODIMONGO/MOSPOLI_LMS
```

#!/usr/bin/env node
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '../..')
const staticDir = path.resolve(process.env.STATIC_DIR ?? path.join(repoRoot, 'dist'))
const port = Number(process.env.FRONTEND_PORT ?? 5173)
const upstream = process.env.AI_NAVIGATION_UPSTREAM ?? 'http://127.0.0.1:3001'

const mimeTypes = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.html', 'text/html; charset=utf-8'],
  ['.ico', 'image/x-icon'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.map', 'application/json; charset=utf-8'],
  ['.png', 'image/png'],
  ['.svg', 'image/svg+xml'],
  ['.txt', 'text/plain; charset=utf-8'],
  ['.woff', 'font/woff'],
  ['.woff2', 'font/woff2'],
])

const server = http.createServer(async (request, response) => {
  try {
    const url = new URL(request.url ?? '/', `http://${request.headers.host ?? 'localhost'}`)

    if (url.pathname.startsWith('/api/')) {
      proxyApi(request, response, url)
      return
    }

    await serveStatic(response, url.pathname)
  } catch (error) {
    response.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' })
    response.end(error instanceof Error ? error.message : 'Internal server error')
  }
})

server.listen(port, '0.0.0.0', () => {
  console.log(`frontend static/proxy server listening on :${port}`)
  console.log(`serving ${staticDir}`)
  console.log(`proxying /api/* to ${upstream}`)
})

function proxyApi(request, response, url) {
  const target = new URL(url.pathname + url.search, upstream)
  const headers = { ...request.headers, host: target.host }

  const proxyRequest = http.request(
    target,
    {
      method: request.method,
      headers,
    },
    (proxyResponse) => {
      response.writeHead(proxyResponse.statusCode ?? 502, proxyResponse.headers)
      proxyResponse.pipe(response)
    },
  )

  proxyRequest.on('error', (error) => {
    response.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
    response.end(JSON.stringify({ error: 'Bad gateway', message: error.message }))
  })

  request.pipe(proxyRequest)
}

async function serveStatic(response, pathname) {
  const requestedPath = decodeURIComponent(pathname)
  const normalizedPath = requestedPath === '/' ? '/index.html' : requestedPath
  const filePath = path.resolve(staticDir, `.${normalizedPath}`)

  if (!filePath.startsWith(staticDir + path.sep) && filePath !== staticDir) {
    response.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' })
    response.end('Forbidden')
    return
  }

  const resolvedPath = await resolveFile(filePath)
  const contentType = mimeTypes.get(path.extname(resolvedPath)) ?? 'application/octet-stream'
  response.writeHead(200, {
    'Content-Type': contentType,
    'Cache-Control': resolvedPath.endsWith('index.html') ? 'no-cache' : 'public, max-age=31536000, immutable',
  })
  fs.createReadStream(resolvedPath).pipe(response)
}

async function resolveFile(filePath) {
  try {
    const stats = await fs.promises.stat(filePath)
    if (stats.isFile()) {
      return filePath
    }
  } catch {
    // Fall through to SPA fallback.
  }

  return path.join(staticDir, 'index.html')
}

#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/content/MOSPOLI_LMS}"
MODEL_DIR="${MODEL_DIR:-$REPO_DIR/models}"
MODEL_FILE="${MODEL_FILE:-qwen3-embedding-4b-q5_k_m.gguf}"
MODEL_PATH="${MODEL_PATH:-$MODEL_DIR/$MODEL_FILE}"
MODEL_URL="${MODEL_URL:-https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF/resolve/main/Qwen3-Embedding-4B-Q5_K_M.gguf?download=true}"
LLAMA_DIR="${LLAMA_DIR:-/content/llama.cpp}"
LLAMA_SERVER_BIN="${LLAMA_SERVER_BIN:-$LLAMA_DIR/build/bin/llama-server}"
LLAMA_PORT="${LLAMA_PORT:-8080}"
AI_PORT="${AI_PORT:-3001}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
LOG_DIR="${LOG_DIR:-$REPO_DIR/.colab/logs}"
DOWNLOAD_MODEL="${DOWNLOAD_MODEL:-true}"
BUILD_LLAMA="${BUILD_LLAMA:-true}"
START_TUNNEL="${START_TUNNEL:-none}"
EMBEDDING_MOCK="${EMBEDDING_MOCK:-false}"

dump_diagnostics() {
  local exit_code=$?
  echo
  echo "start-colab.sh failed with exit code $exit_code"
  echo "Diagnostics:"
  echo "  node: $(node --version 2>/dev/null || echo missing)"
  echo "  npm:  $(npm --version 2>/dev/null || echo missing)"
  echo "  cwd:  $(pwd)"
  echo
  echo "Listening ports:"
  (ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null || true) | grep -E ":($LLAMA_PORT|$AI_PORT|$FRONTEND_PORT)\b" || true
  echo
  echo "Processes:"
  ps -ef | grep -E "llama-server|ai-navigation-service/dist/server.js|deploy/colab/serve-frontend.mjs" | grep -v grep || true
  echo
  for log_file in "$LOG_DIR/llama-server.log" "$LOG_DIR/ai-navigation-service.log" "$LOG_DIR/frontend.log"; do
    if [[ -f "$log_file" ]]; then
      echo "--- tail $log_file ---"
      tail -n 80 "$log_file" || true
    fi
  done
  exit "$exit_code"
}

trap dump_diagnostics ERR

wait_for_http() {
  local name="$1"
  local url="$2"

  echo "Waiting for $name at $url"
  for _ in $(seq 1 180); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done

  echo "$name did not become ready: $url" >&2
  return 1
}

install_cloudflared() {
  if command -v cloudflared >/dev/null 2>&1; then
    return 0
  fi

  local deb="/tmp/cloudflared-linux-amd64.deb"
  wget -q -O "$deb" https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  dpkg -i "$deb"
}

install_node_dependencies() {
  local dir="$1"
  if [[ -f "$dir/package-lock.json" ]]; then
    (cd "$dir" && npm ci)
  else
    (cd "$dir" && npm install)
  fi
}

check_node_version() {
  node -e '
    const [major, minor] = process.versions.node.split(".").map(Number)
    if (major < 20 || (major === 20 && minor < 19)) {
      console.error(`Node.js ${process.versions.node} is too old. Install Node.js 20.19+ or 22.12+ before running this script.`)
      process.exit(1)
    }
  '
}

if [[ "$EMBEDDING_MOCK" != "true" ]] && ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "Warning: nvidia-smi was not found. In Colab, enable Runtime -> Change runtime type -> GPU before building llama.cpp with CUDA." >&2
fi

mkdir -p "$MODEL_DIR" "$LOG_DIR"
cd "$REPO_DIR"
check_node_version

if [[ "$EMBEDDING_MOCK" != "true" ]]; then
  if [[ ! -f "$MODEL_PATH" ]]; then
    if [[ "$DOWNLOAD_MODEL" != "true" ]]; then
      echo "Model is missing and DOWNLOAD_MODEL=false: $MODEL_PATH" >&2
      exit 1
    fi
    echo "Downloading model to $MODEL_PATH"
    wget -c -O "$MODEL_PATH" "$MODEL_URL"
  fi

  if [[ ! -d "$LLAMA_DIR/.git" ]]; then
    git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "$LLAMA_DIR"
  fi

  if [[ "$BUILD_LLAMA" == "true" || ! -x "$LLAMA_SERVER_BIN" ]]; then
    cmake -S "$LLAMA_DIR" -B "$LLAMA_DIR/build" -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
    cmake --build "$LLAMA_DIR/build" --config Release -j"$(nproc)"
  fi
else
  echo "EMBEDDING_MOCK=true: skipping GGUF download, llama.cpp clone/build, and llama.cpp server startup."
fi

install_node_dependencies "$REPO_DIR"
install_node_dependencies "$REPO_DIR/ai-navigation-service"

npm run build
(cd ai-navigation-service && npm run build)

if [[ "$EMBEDDING_MOCK" != "true" ]]; then
  pkill -f "$LLAMA_SERVER_BIN" 2>/dev/null || true
fi
pkill -f "ai-navigation-service/dist/server.js" 2>/dev/null || true
pkill -f "deploy/colab/serve-frontend.mjs" 2>/dev/null || true

if [[ "$EMBEDDING_MOCK" != "true" ]]; then
  nohup "$LLAMA_SERVER_BIN" \
    -m "$MODEL_PATH" \
    --embedding \
    -ub "${LLAMA_UBATCH:-8192}" \
    --host 0.0.0.0 \
    --port "$LLAMA_PORT" \
    > "$LOG_DIR/llama-server.log" 2>&1 &

  wait_for_http "llama.cpp" "http://127.0.0.1:$LLAMA_PORT/health"
fi

nohup env \
  PORT="$AI_PORT" \
  EMBEDDING_BASE_URL="http://127.0.0.1:$LLAMA_PORT" \
  EMBEDDING_MODEL="${EMBEDDING_MODEL:-qwen3-embedding-q5-k-m}" \
  EMBEDDING_MOCK="$EMBEDDING_MOCK" \
  ALLOW_EMBEDDING_FALLBACK="${ALLOW_EMBEDDING_FALLBACK:-false}" \
  node ai-navigation-service/dist/server.js \
  > "$LOG_DIR/ai-navigation-service.log" 2>&1 &

wait_for_http "ai-navigation-service" "http://127.0.0.1:$AI_PORT/health"

nohup env \
  FRONTEND_PORT="$FRONTEND_PORT" \
  AI_NAVIGATION_UPSTREAM="http://127.0.0.1:$AI_PORT" \
  node deploy/colab/serve-frontend.mjs \
  > "$LOG_DIR/frontend.log" 2>&1 &

wait_for_http "frontend" "http://127.0.0.1:$FRONTEND_PORT/"

echo "Services are running."
if [[ "$EMBEDDING_MOCK" == "true" ]]; then
  echo "  llama.cpp:             skipped (EMBEDDING_MOCK=true)"
else
  echo "  llama.cpp:             http://127.0.0.1:$LLAMA_PORT"
fi
echo "  ai-navigation-service: http://127.0.0.1:$AI_PORT"
echo "  frontend:              http://127.0.0.1:$FRONTEND_PORT"
echo "Logs: $LOG_DIR"
echo
echo "Local checks:"
echo "  curl -fsS http://127.0.0.1:$FRONTEND_PORT/"
echo "  curl -fsS http://127.0.0.1:$AI_PORT/health"

case "$START_TUNNEL" in
  cloudflared)
    install_cloudflared
    echo "Starting Cloudflare quick tunnel. Open the trycloudflare.com URL printed below."
    cloudflared tunnel --url "http://127.0.0.1:$FRONTEND_PORT"
    ;;
  localtunnel)
    echo "Starting localtunnel. If it asks for a password, use Colab's public IP from: curl ipv4.icanhazip.com"
    npx --yes localtunnel --port "$FRONTEND_PORT" --local-host 127.0.0.1
    ;;
  none)
    echo "Tunnel disabled. Set START_TUNNEL=cloudflared or START_TUNNEL=localtunnel to expose the frontend."
    ;;
  *)
    echo "Unknown START_TUNNEL=$START_TUNNEL. Use cloudflared, localtunnel, or none." >&2
    exit 1
    ;;
esac
