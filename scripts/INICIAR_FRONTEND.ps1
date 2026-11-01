$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $ProjectRoot 'frontend')
npm ci
if ($LASTEXITCODE -ne 0) { throw 'Falló npm ci' }
npm run dev
