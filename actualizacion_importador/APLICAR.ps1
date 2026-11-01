$ErrorActionPreference = 'Stop'
$ProjectRoot = 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
if (-not (Test-Path (Join-Path $ProjectRoot 'docker-compose.yml'))) {
    throw 'No se encontró el proyecto en la ruta Windows autorizada.'
}
function Get-TextHash([string]$FilePath) {
    $Content = [System.IO.File]::ReadAllText($FilePath).Replace("`r`n", "`n").TrimStart([char]0xFEFF)
    $Hasher = [System.Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($Hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($Content)))).Replace('-', '') }
    finally { $Hasher.Dispose() }
}
$Files = @(
    @{ Path = 'backend/app/narrative.py'; Hashes = @('E5C74DC87393DC3EEA745993562F31F906E2DEBCE313923555BA53745E142B3B','CF5DB6FC42151DD1B65F7A0BB74383A289D8ABA9226BABC80627C89E9C50C725') }
    @{ Path = 'backend/app/main.py'; Hashes = @('76E0252B2B3CF87E019934E2D567834999A5DE2E4A73B05AE8D6409F438D6021','85C7606059C164702CADCCE5D0B3D6EC8089597F31E6C7F4B95B9E0CCB074B5F','034A61045C889F3E8D157B0AD3F0F3E966B1C350226A32493A03C9E564895A85') }
    @{ Path = 'frontend/src/main.tsx'; Hashes = @('D5C0C9D1DBFD21BAE102CC55A662B71A5EB47E226A1B8457EC562B21959A7DB0','C1D55C51514C9A03FED146368D4A6213C03FD1DDA4B26872441C297BF4C59C5D') }
    @{ Path = 'backend/tests/test_narrative.py'; Hashes = @('9F888D84BBFADCC72C9A73CC83000BE1CC0E65788DA594A4BCAF0DF8C5925EB9') }
)
# Validate all targets before copying any file.
foreach ($Entry in $Files) {
    $Target = Join-Path $ProjectRoot $Entry.Path
    $Source = Join-Path $PSScriptRoot $Entry.Path
    if (-not (Test-Path $Source)) { throw "Falta archivo de actualización: $Source" }
    if ((Get-TextHash $Source) -ne $Entry.Hashes[-1]) { throw "Archivo de actualización alterado: $Source" }
    if ((Test-Path $Target) -and ((Get-TextHash $Target) -notin $Entry.Hashes)) {
        throw "El archivo $Target tiene cambios no reconocidos. No se aplicó la actualización. Comparar antes de continuar."
    }
}
$BackupRoot = Join-Path $ProjectRoot ('backups\importador-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
foreach ($Entry in $Files) {
    $Target = Join-Path $ProjectRoot $Entry.Path
    $Source = Join-Path $PSScriptRoot $Entry.Path
    if (Test-Path $Target) {
        $Backup = Join-Path $BackupRoot $Entry.Path
        New-Item -ItemType Directory -Force -Path (Split-Path $Backup -Parent) | Out-Null
        Copy-Item -LiteralPath $Target -Destination $Backup
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $Target -Parent) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Target -Force
}
Write-Host "Actualización aplicada. Copia de seguridad: $BackupRoot"
Set-Location $ProjectRoot
docker compose up -d --build backend
if ($LASTEXITCODE -ne 0) { throw 'Falló la reconstrucción. Los respaldos permanecen disponibles.' }
Write-Host 'Backend reconstruido. Recarga el navegador y crea un NUEVO proyecto para reimportar el libro.'
Write-Host 'No se modificaron la base de datos ni los audios de los proyectos existentes.'
