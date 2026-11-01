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
    @{ Path = 'backend/app/main.py'; Hashes = @('E466171849F2B4FA6411D2635065C6C50A24D6E734D00128ECE9738AB9EB1561','B85C79651998947730A1C98E04CD0538A45578237C93C5B92BC447F711E1DB2A') }
    @{ Path = 'backend/app/narrative.py'; Hashes = @('CF5DB6FC42151DD1B65F7A0BB74383A289D8ABA9226BABC80627C89E9C50C725','3771C58962E6D2B3D6052BC1961B6FA88337515798A0B2A6C129D7311B2E528F') }
    @{ Path = 'backend/app/scenes.py'; Hashes = @('463DC4AE0992A01845CFDFE06E525F568946F4D789945E2D697DBC8648B3B78E') }
    @{ Path = 'frontend/src/main.tsx'; Hashes = @('FE523973B769731CA3538D9BE01EC5EB89CB23DEA60EFFC53FFFE762CEBB2DA7','E8D62D8E51683EB37D1A54501E3CD52D573055F57B1DB7F30072D7A950BE3326') }
    @{ Path = 'frontend/src/style.css'; Hashes = @('E75DF2864B2FE9C5DF0B618B0B1579CF496C620DEA03D0DC2511163DE87289EB','97D3D83D2BF23421FBA5756F62CB9DEB152BCFFB2556A8D20158D06F94F8AEF3') }
    @{ Path = 'backend/tests/test_scenes.py'; Hashes = @('3D40DCD0E42598B335BAB9DC06CB0FE231C3C61F81F3F1C30110549F85DFF567') }
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
$BackupRoot = Join-Path $ProjectRoot ('backups\escenas-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
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
Write-Host 'Backend reconstruido. Recarga el navegador y abre tu proyecto. Las escenas se actualizan sin reimportar ni perder voces.'
Write-Host 'No se modificaron la base de datos ni los audios de los proyectos existentes.'
