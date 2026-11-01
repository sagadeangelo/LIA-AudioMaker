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
    @{ Path = 'frontend/src/main.tsx'; Hashes = @('E8D62D8E51683EB37D1A54501E3CD52D573055F57B1DB7F30072D7A950BE3326','DE5F5270E477041E220E93FD0603FDD860235217D34CF705AD0255C52641F689') }
    @{ Path = 'frontend/src/selection.ts'; Hashes = @('73BF9FE498C45BA4CF4B673BABFD626B0F0363B53B59706DA59612076CDE3066') }
    @{ Path = 'frontend/tests/selection.test.mjs'; Hashes = @('661323FB5B4479B66904C7AABC0BEA1F3E3A3717CC3DCDDC28C8AC7CE3270800') }
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
$BackupRoot = Join-Path $ProjectRoot ('backups\seleccion-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
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
Write-Host 'Corrección de interfaz aplicada. Recarga el navegador con Ctrl+F5. No hay cambios en backend ni en datos.'
