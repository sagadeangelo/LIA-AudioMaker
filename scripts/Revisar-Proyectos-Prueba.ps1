param(
    [string]$Repo = 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker',
    [ValidateSet('Revisar','Papelera','Restaurar')][string]$Modo = 'Revisar',
    [string]$Informe = '',
    [string[]]$Ids = @(),
    [string]$Respaldo = ''
)
$ErrorActionPreference = 'Stop'
$Repo = [IO.Path]::GetFullPath($Repo)
$ScriptPython = Join-Path $PSScriptRoot 'project_test_audit.py'
if (!(Test-Path -LiteralPath (Join-Path $Repo 'docker-compose.yml'))) { throw 'No se reconoce la carpeta de LIA AudioMaker.' }
if (!(Test-Path -LiteralPath $ScriptPython)) { throw 'Falta project_test_audit.py junto a este script.' }
if ($Modo -eq 'Papelera') {
    if (!$Informe -or !(Test-Path -LiteralPath $Informe -PathType Leaf)) { throw 'Indica -Informe con el JSON generado durante la revision.' }
    if (!$Ids.Count) { throw 'Indica -Ids con los identificadores que revisaste. No se eligen automaticamente.' }
    foreach ($Id in $Ids) { if ($Id -notmatch '^[A-Za-z0-9][A-Za-z0-9-]{0,79}$') { throw 'Identificador no valido.' } }
}
if ($Modo -eq 'Restaurar' -and (!$Respaldo -or !(Test-Path -LiteralPath $Respaldo -PathType Leaf))) { throw 'Indica -Respaldo con respaldo_papelera.json.' }
$Salida = Join-Path $Repo ('mantenimiento\proyectos_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $Salida -Force | Out-Null
$Parametros = @('--mode','audit','--out','/report')
if ($Modo -eq 'Papelera') {
    Copy-Item -LiteralPath $Informe -Destination (Join-Path $Salida 'informe_revisado.json')
    $Parametros = @('--mode','trash','--out','/report','--report','/report/informe_revisado.json','--ids') + $Ids
}
if ($Modo -eq 'Restaurar') {
    Copy-Item -LiteralPath $Respaldo -Destination (Join-Path $Salida 'respaldo_a_restaurar.json')
    $Parametros = @('--mode','restore','--backup','/report/respaldo_a_restaurar.json')
}
Push-Location -LiteralPath $Repo
try {
    & docker compose run --rm --no-deps -T `
        -v "${ScriptPython}:/tool/project_test_audit.py:ro" `
        -v "${Salida}:/report" `
        -e PYTHONDONTWRITEBYTECODE=1 `
        backend python /tool/project_test_audit.py @Parametros
    if ($LASTEXITCODE -ne 0) { throw 'La operacion se detuvo. No borres proyectos ni volumenes; comparte el mensaje.' }
    Write-Host "`nResultado guardado en: $Salida"
    if ($Modo -eq 'Revisar') {
        Write-Host 'Abre informe_proyectos.csv y revisa los candidatos. Esta operacion fue solo lectura.'
        Write-Host 'Comparte las lineas CANDIDATO para preparar los IDs exactos que quieres ocultar.'
    }
} finally { Pop-Location }
