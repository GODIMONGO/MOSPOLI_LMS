param(
    [int]$AppPort = 5000,
    [int]$InfinityPort = 7997,
    [int]$QdrantPort = 6333,
    [string]$Python = "3.10",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Runtime = Join-Path $Root ".runtime"
$Logs = Join-Path $Runtime "logs"
$Pids = Join-Path $Runtime "pids"
$QdrantHome = Join-Path $Runtime "qdrant"
$QdrantExe = Join-Path $QdrantHome "qdrant.exe"

New-Item -ItemType Directory -Force $Runtime, $Logs, $Pids | Out-Null
Set-Location $Root

function Test-PortOpen {
    param([int]$Port)
    return (Test-NetConnection -ComputerName "127.0.0.1" -Port $Port -WarningAction SilentlyContinue).TcpTestSucceeded
}

function Wait-Port {
    param([int]$Port, [string]$Name, [int]$TimeoutSeconds = 1800)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortOpen -Port $Port) {
            Write-Host "$Name ready on port $Port"
            return
        }
        Start-Sleep -Seconds 3
    }
    throw "$Name did not become ready on port $Port"
}

function Start-LoggedProcess {
    param([string]$Name, [string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory = $Root)
    $out = Join-Path $Logs "$Name.out.log"
    $err = Join-Path $Logs "$Name.err.log"
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
    Set-Content -Path (Join-Path $Pids "$Name.pid") -Value $process.Id
    Write-Host "Started $Name (pid $($process.Id))"
}

if (-not $SkipInstall) {
    if (-not (Test-Path ".venv")) {
        uv venv .venv --python $Python
    }
    uv pip install -r requirements.txt
    uv pip install -r requirements-semantic.txt
}

if (-not (Test-Path $QdrantExe)) {
    Write-Host "Downloading portable Qdrant..."
    New-Item -ItemType Directory -Force $QdrantHome | Out-Null
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/qdrant/qdrant/releases/latest"
    $asset = $release.assets | Where-Object { $_.name -eq "qdrant-x86_64-pc-windows-msvc.zip" } | Select-Object -First 1
    if (-not $asset) {
        throw "Could not find Qdrant Windows release asset."
    }
    $archive = Join-Path $Runtime "qdrant.zip"
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $QdrantHome -Force
}

$env:PYTHONIOENCODING = "utf-8"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$env:QDRANT_URL = "http://localhost:$QdrantPort"
$env:QDRANT_COLLECTION = "routes"
$env:INFINITY_BASE_URL = "http://localhost:$InfinityPort"
$env:INFINITY_EMBEDDING_MODEL = "jina-embeddings-v5-text-small"
$env:INFINITY_RERANKER_MODEL = "jina-reranker-v3"
$env:SEMANTIC_ROUTER_SCORE_THRESHOLD = "0.30"
$env:SEMANTIC_ROUTER_AMBIGUITY_MARGIN = "0.08"

if (Test-PortOpen -Port $QdrantPort) {
    Write-Host "Qdrant already responds on port $QdrantPort"
} else {
    Start-LoggedProcess -Name "qdrant" -FilePath $QdrantExe -Arguments @() -WorkingDirectory $Runtime
}
Wait-Port -Port $QdrantPort -Name "Qdrant" -TimeoutSeconds 120

if (Test-PortOpen -Port $InfinityPort) {
    Write-Host "Infinity already responds on port $InfinityPort"
} else {
    Start-LoggedProcess -Name "infinity" -FilePath "uv" -Arguments @(
        "run", "infinity_emb", "v2",
        "--model-id", "jinaai/jina-embeddings-v5-text-small",
        "--served-model-name", "jina-embeddings-v5-text-small",
        "--model-id", "jinaai/jina-reranker-v3",
        "--served-model-name", "jina-reranker-v3",
        "--engine", "torch",
        "--device", "cpu",
        "--host", "127.0.0.1",
        "--port", "$InfinityPort",
        "--no-model-warmup",
        "--no-bettertransformer",
        "--log-level", "info"
    )
}
Wait-Port -Port $InfinityPort -Name "Infinity" -TimeoutSeconds 1800

uv run python -m semantic_router.cli index

if (Test-PortOpen -Port $AppPort) {
    Write-Host "App already responds on port $AppPort"
} else {
    Start-LoggedProcess -Name "app" -FilePath "uv" -Arguments @(
        "run", "flask", "--app", "main", "run",
        "--host", "127.0.0.1",
        "--port", "$AppPort"
    )
}

Write-Host ""
Write-Host "MOSPOLI_LMS is ready: http://127.0.0.1:$AppPort"
Write-Host "Login: student / 123 or admin / admin"
Write-Host "Stop everything with: .\scripts\stop_native.ps1"
