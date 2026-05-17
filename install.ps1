# Voice-to-Text · Night City — Windows installer
# Uso:  powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

function Test-Cmd($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

Write-Host ""
Write-Host "==================================================="
Write-Host "  VOICE-TO-TEXT // NIGHT CITY -- Windows installer"
Write-Host "==================================================="
Write-Host ""

# 1. Python
if (-not (Test-Cmd "python")) {
    Write-Host "[X] Python no encontrado." -ForegroundColor Red
    Write-Host "    Instala: winget install Python.Python.3.12 -e"
    exit 1
}
$pyv = (python --version) 2>&1
Write-Host "[OK] $pyv" -ForegroundColor Green

# 2. ffmpeg
if (-not (Test-Cmd "ffmpeg")) {
    Write-Host "[!] ffmpeg no encontrado en PATH." -ForegroundColor Yellow
    Write-Host "    Instala: winget install Gyan.FFmpeg -e"
    Write-Host "    (Sin ffmpeg solo podras subir mp3/wav, no video ni m4a/opus/flac)"
} else {
    $fv = (ffmpeg -version | Select-Object -First 1)
    Write-Host "[OK] $fv" -ForegroundColor Green
}

# 3. Crear venv si no existe
if (-not (Test-Path ".venv")) {
    Write-Host "[*] Creando entorno virtual en .venv ..."
    python -m venv .venv
} else {
    Write-Host "[OK] .venv ya existe" -ForegroundColor Green
}

# 4. Activar venv e instalar
Write-Host "[*] Activando venv e instalando dependencias..."
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt

# 5. GPU NVIDIA?
$nvidia = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue |
          Where-Object { $_.Name -match "NVIDIA" }
if ($nvidia) {
    Write-Host ""
    Write-Host "[i] GPU NVIDIA detectada: $($nvidia.Name)" -ForegroundColor Cyan
    Write-Host "    Para activar CUDA (5-15x mas rapido):"
    Write-Host "       1. Instala CUDA Toolkit 12.x  -> https://developer.nvidia.com/cuda-downloads"
    Write-Host "       2. Instala cuDNN 9 for CUDA 12 -> https://developer.nvidia.com/cudnn"
    Write-Host "       3. Antes de arrancar el server, ejecuta:"
    Write-Host "          `$env:WHISPER_DEVICE = `"cuda`""
    Write-Host "          `$env:WHISPER_COMPUTE = `"float16`""
}

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "  INSTALACION COMPLETA" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para arrancar:"
Write-Host "    .\.venv\Scripts\Activate.ps1"
Write-Host "    python server.py"
Write-Host ""
Write-Host "Despues abre:  http://localhost:8000"
Write-Host ""
