$ErrorActionPreference = 'Stop'
$ProjectRoot = 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
$Target = Join-Path $ProjectRoot 'frontend\src\main.tsx'
$Helper = Join-Path $ProjectRoot 'frontend\src\selection.ts'
if (-not (Test-Path $Target) -or -not (Test-Path $Helper)) {
    throw 'Se requiere la corrección 0.1.5 o la versión 0.1.6 instalada en la ruta autorizada.'
}
if (-not ([IO.File]::ReadAllText($Helper).Contains('export function isDialogueCandidate'))) {
    throw 'El helper de selección no corresponde a la versión esperada. No se modificó ningún archivo.'
}
$Content = [IO.File]::ReadAllText($Target).Replace("`r`n", "`n").TrimStart([char]0xFEFF)
$Changes = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'cambios.json') -Raw -Encoding UTF8 | ConvertFrom-Json
# Validate and apply all replacements in memory before touching the file.
foreach ($Change in $Changes) {
    $OldCount = [regex]::Matches($Content, [regex]::Escape($Change.old)).Count
    $NewCount = [regex]::Matches($Content, [regex]::Escape($Change.new)).Count
    if ($NewCount -eq 1) { continue }
    if ($OldCount -ne 1) { throw 'El código del selector tiene cambios no reconocidos. No se modificó ningún archivo.' }
    $Content = $Content.Replace($Change.old, $Change.new)
}
$FooterPattern = 'LIA AUDIOMAKER · 0\.1\.(5|6|7)'
if ([regex]::Matches($Content,$FooterPattern).Count -ne 1) {
    throw 'No se identificó una versión compatible de la interfaz. No se modificó ningún archivo.'
}
$Content = [regex]::Replace($Content, $FooterPattern, 'LIA AUDIOMAKER · 0.1.7')
$BackupRoot = Join-Path $ProjectRoot ('backups\filtro-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
Copy-Item -LiteralPath $Target -Destination (Join-Path $BackupRoot 'main.tsx')
[IO.File]::WriteAllText($Target,$Content,[Text.UTF8Encoding]::new($false))
Write-Host "Corrección aplicada. Respaldo: $BackupRoot"
Write-Host 'Mantén Vite abierto y recarga con Ctrl+F5. No se requiere reiniciar Docker ni reimportar el libro.'
