$ErrorActionPreference = "SilentlyContinue"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Pids = Join-Path $Root ".runtime\pids"

function Stop-Tree {
    param([int]$RootProcessId)
    $children = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $RootProcessId }
    foreach ($child in $children) {
        Stop-Tree -RootProcessId ([int]$child.ProcessId)
    }
    Stop-Process -Id $RootProcessId -Force
}

if (Test-Path $Pids) {
    Get-ChildItem $Pids -Filter "*.pid" | ForEach-Object {
        $processId = [int](Get-Content $_.FullName)
        Stop-Tree -RootProcessId $processId
        Remove-Item $_.FullName -Force
    }
}

Write-Host "Native MOSPOLI_LMS services stopped."
