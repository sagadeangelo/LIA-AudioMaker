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
    @{ Path = 'backend/app/main.py'; Hashes = @('B85C79651998947730A1C98E04CD0538A45578237C93C5B92BC447F711E1DB2A','487119635F6F805806E4EB12902960D1AB9A66A36F924C36021AD1675352CD30') }
    @{ Path = 'frontend/src/main.tsx'; Hashes = @('DE5F5270E477041E220E93FD0603FDD860235217D34CF705AD0255C52641F689','E8D62D8E51683EB37D1A54501E3CD52D573055F57B1DB7F30072D7A950BE3326','5DA1CE9B06FD547226B032C421A5BB577248149149A1300B82E782633C03D113') }
    @{ Path = 'frontend/src/selection.ts'; Hashes = @('73BF9FE498C45BA4CF4B673BABFD626B0F0363B53B59706DA59612076CDE3066') }
    @{ Path = 'frontend/src/style.css'; Hashes = @('97D3D83D2BF23421FBA5756F62CB9DEB152BCFFB2556A8D20158D06F94F8AEF3','0D636A85918F0398048E720BFFFAF1F556B530DF7FDCFCDE7F79EA6B9E7C4935') }
    @{ Path = 'frontend/src/ProjectTrash.tsx'; Hashes = @('FD6E172B865CA974F306279C5490F984E0F0361FA2E035D79350D8C9CB135828') }
    @{ Path = 'backend/tests/test_projects.py'; Hashes = @('F08DAE8C38D842D4599E33BD03B50D5151753052497E512D8EA76C0DE0524736') }
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
$BackupRoot = Join-Path $ProjectRoot ('backups\proyectos-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
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
Write-Host 'Backend reconstruido. Recarga el navegador: Eliminar proyecto y Papelera aparecen en la barra superior.'
Write-Host 'No se modificaron la base de datos ni los audios de los proyectos existentes.'
