param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$dashboardRepo = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $dashboardRepo
$env:PYTHONUTF8 = '1'
python dashboard/server.py --port $Port
