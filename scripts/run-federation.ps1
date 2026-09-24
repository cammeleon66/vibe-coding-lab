<#
.SYNOPSIS
  Starts the three federated services locally: UMC Utrecht (8101), Heidelberg (8102) and the hub (8100).
.EXAMPLE
  ./scripts/run-federation.ps1            # builds nothing; serves frontend/dist from the hub
  ./scripts/run-federation.ps1 -Build     # runs npm run build first
  Stop with Ctrl+C; all three processes are stopped together.
#>
param(
    [switch]$Build,
    [string]$DataDir = (Join-Path $PSScriptRoot '..\.fed-data')
)
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }
if ($Build) { Push-Location (Join-Path $root 'frontend'); npm run build; Pop-Location }

$services = @(
    @{ Site = 'nl'; Port = 8101 },
    @{ Site = 'de'; Port = 8102 },
    @{ Site = 'hub'; Port = 8100 }
)
$processes = foreach ($service in $services) {
    $env:PYTHONPATH = Join-Path $root 'src'
    $env:SITE = $service.Site
    $env:FED_DATA_DIR = $DataDir
    $env:FRONTEND_DIST = Join-Path $root 'frontend\dist'
    Start-Process -FilePath $python -ArgumentList @('-m', 'uvicorn', 'fednet.main:app', '--host', '127.0.0.1',
        '--port', $service.Port) -WorkingDirectory $root -NoNewWindow -PassThru
}
Write-Host 'Federation running: http://127.0.0.1:8100  (UMC Utrecht :8101, Heidelberg :8102). Ctrl+C to stop.'
try {
    Wait-Process -Id $processes.Id
}
finally {
    $processes | Where-Object { -not $_.HasExited } | ForEach-Object { Stop-Process -Id $_.Id }
}
