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
    @{ Path = 'frontend/src/main.tsx'; Hashes = @('40910DA88D9ECF3BE8C81C09FFC925B542F8158BE0BA8AB2AC0CEF2E628195F9','5DA1CE9B06FD547226B032C421A5BB577248149149A1300B82E782633C03D113','B0504D2D8D40892B4C8DAACBE12D5931F5DE7B65EA4161797D4CDA2A1112E9D3') }
    @{ Path = 'frontend/src/fragmentFilters.ts'; Hashes = @('CBA50F9E0011880711B93303827067D7D8ED03E15C2573E342E48314C3BFCC93') }
    @{ Path = 'frontend/tests/fragmentFilters.test.mjs'; Hashes = @('78E5E7516F759E6A825F61BC374A45C19800BAC2D6FC8A84EE5B98264BDE0AFA') }
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
$BackupRoot = Join-Path $ProjectRoot ('backups\vista-simple-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
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
Write-Host 'Vista simplificada aplicada. Recarga con Ctrl+F5. Todos los fragmentos aparecen por defecto; no hay cambios en backend ni en datos.'
