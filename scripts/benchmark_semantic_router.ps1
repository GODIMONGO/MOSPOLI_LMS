param(
    [string]$Cases = "data/semantic_router_eval.json",
    [int]$Rounds = 2,
    [int]$Warmup = 1
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$env:PYTHONIOENCODING = "utf-8"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

uv run python -m semantic_router.cli benchmark --cases $Cases --rounds $Rounds --warmup $Warmup
