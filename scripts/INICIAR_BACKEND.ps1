$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) { py -3.12 -m venv .venv; if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python' } }
& '.\.venv\Scripts\python.exe' -m pip install -r backend\requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación de dependencias' }
Set-Location backend
& '..\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
