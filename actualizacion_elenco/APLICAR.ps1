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
    @{ Path = 'backend/app/main.py'; Hashes = @('034A61045C889F3E8D157B0AD3F0F3E966B1C350226A32493A03C9E564895A85','E75BC684A105A6470AA5001CF9A376D2861A7FE22370DD21D0C3FCD72C6DCF30') }
    @{ Path = 'backend/app/casting.py'; Hashes = @('A3DF7D15F3AF848B44896CF7111BDA51F998DA4F345699C90C1E878EA85B912D') }
    @{ Path = 'backend/app/narrative.py'; Hashes = @('CF5DB6FC42151DD1B65F7A0BB74383A289D8ABA9226BABC80627C89E9C50C725') }
    @{ Path = 'frontend/src/main.tsx'; Hashes = @('C1D55C51514C9A03FED146368D4A6213C03FD1DDA4B26872441C297BF4C59C5D','EEB0C8D6362B042B47DBA1476D9DDB6900D54431B8F6D1BF69E3F78BE899D7C5') }
    @{ Path = 'frontend/src/style.css'; Hashes = @('D262039DE1B40984F5F69A95002B1D3818177C46E7922E5F0C50E945DE9B1FD4','A865C163AD4A35F9E4B63F6F6647AD4360F811052B8A0C84798864585AAC2090') }
    @{ Path = 'frontend/src/CastPanel.tsx'; Hashes = @('8DAB5AFB6CF87AB75460BC42CB1D7BB37DDE181AFC2BD83A788BDE4197E77AC0') }
    @{ Path = 'backend/tests/test_casting.py'; Hashes = @('F0081DCE2C7DDAA1E78C6D1D7566EDDC54D4BFF5545EB764934FA21B0F538164') }
    @{ Path = 'backend/tests/conftest.py'; Hashes = @('C2F4C1C617DDB86DD2BF7B0121F1A005A3FC2B20F8E2018B551FA5180A2CCDE6') }
    @{ Path = 'backend/tests/test_flow.py'; Hashes = @('28CBD4CA2B97207045545A199BF002F4DA097ED0E5F1D866E5A330BB38F97183','ABA2A5CA12CA3AE8458E81DDAC1F82309F5020918BA64AFF88870E732B072DC7') }
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
$BackupRoot = Join-Path $ProjectRoot ('backups\elenco-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
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
Write-Host 'Backend reconstruido. Recarga el navegador y abre tu proyecto existente: el elenco se construye sin reimportar.'
Write-Host 'No se modificaron la base de datos ni los audios de los proyectos existentes.'
