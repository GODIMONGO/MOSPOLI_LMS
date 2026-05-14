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
