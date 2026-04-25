param(
    [string]$Cases = "data/semantic_router_eval.json",
    [switch]$Reindex
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$env:PYTHONIOENCODING = "utf-8"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

if ($Reindex) {
    uv run python -m semantic_router.cli index
}

uv run python -m semantic_router.cli check
uv run python -m semantic_router.cli evaluate --cases $Cases
