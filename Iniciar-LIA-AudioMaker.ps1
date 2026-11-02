# LIA AudioMaker - Iniciador local Windows
# Ejecutar desde PowerShell: powershell.exe -ExecutionPolicy Bypass -File .\Iniciar-LIA-AudioMaker.ps1
$ErrorActionPreference = 'Stop'
$ProjectRoot = 'C:\LIA_RECUPERACION\REPOS_GITHUB\lia_audiomaker'
$FrontendUrl = 'http://127.0.0.1:5174'
$BackendHealthUrl = 'http://127.0.0.1:8000/docs'

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Test-Http([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Wait-Http([string]$Url, [int]$TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Http $Url) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

try {
    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw "No existe la carpeta del proyecto: $ProjectRoot"
    }
    Set-Location -LiteralPath $ProjectRoot
    if (-not (Test-Path -LiteralPath '.\docker-compose.yml')) {
        throw 'No se encontro docker-compose.yml en la raiz del proyecto.'
    }
    if (-not (Test-Path -LiteralPath '.\frontend\package.json')) {
        throw 'No se encontro frontend\package.json.'
    }

    Write-Step 'Comprobando Docker Desktop'
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) { throw 'Docker no esta disponible en PATH. Abre Docker Desktop e intenta de nuevo.' }

    & docker info --format '{{.ServerVersion}}' *> $null
    if ($LASTEXITCODE -ne 0) {
        $dockerDesktop = @(
            "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
            "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe"
        ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if ($dockerDesktop) {
            Write-Host 'Abriendo Docker Desktop...'
            Start-Process -FilePath $dockerDesktop | Out-Null
        } else {
            Write-Host 'Abre Docker Desktop manualmente si no se inicia solo.' -ForegroundColor Yellow
        }
        $dockerReady = $false
        for ($i = 0; $i -lt 60; $i++) {
            Start-Sleep -Seconds 3
            & docker info --format '{{.ServerVersion}}' *> $null
            if ($LASTEXITCODE -eq 0) { $dockerReady = $true; break }
        }
        if (-not $dockerReady) { throw 'Docker no respondio despues de 3 minutos.' }
    }
    Write-Host 'Docker disponible.' -ForegroundColor Green

    Write-Step 'Iniciando servicios de Docker Compose'
    & docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw 'docker compose up -d devolvio un error.' }

    Write-Step 'Comprobando backend FastAPI'
    if (Wait-Http $BackendHealthUrl 90) {
        Write-Host "Backend disponible: $BackendHealthUrl" -ForegroundColor Green
    } else {
        Write-Host 'El backend no respondio en /docs; revisa docker compose logs backend.' -ForegroundColor Yellow
    }

    Write-Step 'Iniciando frontend React/Vite'
    if (-not (Test-Http $FrontendUrl)) {
        $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if (-not $npm) { throw 'No se encontro npm.cmd. Revisa la instalacion de Node.js.' }
        $frontendPath = Join-Path $ProjectRoot 'frontend'
        if (-not (Test-Path -LiteralPath (Join-Path $frontendPath 'node_modules'))) {
            throw 'Falta frontend\node_modules. Ejecuta npm.cmd install dentro de frontend antes de iniciar.'
        }
        # Nueva ventana visible para consultar errores y detener Vite con Ctrl+C.
        $viteCommand = "Set-Location -LiteralPath '$frontendPath'; npm.cmd run dev -- --host 127.0.0.1 --port 5174 --strictPort"
        Start-Process -FilePath 'powershell.exe' -ArgumentList @(
            '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $viteCommand
        ) | Out-Null
    } else {
        Write-Host 'Frontend ya disponible; no se iniciara una segunda instancia.' -ForegroundColor Green
    }

    if (-not (Wait-Http $FrontendUrl 45)) {
        throw 'El frontend no respondio en el puerto 5174. Revisa la ventana de Vite.'
    }
    Write-Host "Frontend disponible: $FrontendUrl" -ForegroundColor Green

    Write-Step 'Abriendo LIA AudioMaker'
    Start-Process $FrontendUrl | Out-Null
    Write-Host "`nLIA AudioMaker listo." -ForegroundColor Green
    Write-Host "Frontend: $FrontendUrl"
    Write-Host "Backend:  $BackendHealthUrl"
    Write-Host 'Para detener los contenedores: docker compose stop'
    Write-Host 'Para detener el frontend: Ctrl+C en la ventana de Vite.'
} catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'No se han eliminado archivos ni bases de datos.' -ForegroundColor Yellow
    exit 1
}
