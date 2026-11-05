param([string]$Repo = 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker')
$ErrorActionPreference = 'Stop'
$Repo = [IO.Path]::GetFullPath($Repo)
$Pruebas = Join-Path $Repo 'backend\tests'
$Codigo = Join-Path $Repo 'backend\app'
$Herramientas = $PSScriptRoot
if (!(Test-Path -LiteralPath (Join-Path $Pruebas 'conftest.py'))) { throw 'Falta backend/tests/conftest.py.' }
Push-Location -LiteralPath $Repo
try {
    # Run current source/tests read-only. No production audio volume is used by the test suite.
    & docker compose run --rm --no-deps -T `
        -v "${Pruebas}:/app/tests:ro" `
        -v "${Codigo}:/app/app:ro" `
        -v "${Herramientas}:/tool:ro" `
        -e PYTHONPATH=/app `
        -e PYTHONDONTWRITEBYTECODE=1 `
        -e DATA_DIR=/tmp/lia_test_audio `
        -e DATABASE_URL=sqlite:////tmp/lia_tests_fallback.sqlite `
        backend python -m pytest /app/tests -q -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw 'Hubo una prueba fallida. Comparte la salida. No se uso la base PostgreSQL de tus proyectos.' }
} finally { Pop-Location }
