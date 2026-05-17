#!/usr/bin/env bash
# Voice-to-Text · Night City — macOS / Linux installer
set -euo pipefail

cyan="\033[36m"; green="\033[32m"; yellow="\033[33m"; red="\033[31m"; reset="\033[0m"

echo ""
echo "==================================================="
echo "  VOICE-TO-TEXT // NIGHT CITY -- Unix installer"
echo "==================================================="
echo ""

# 1. Python
if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${red}[X] python3 no encontrado${reset}"
  echo "    macOS:  brew install python@3.12"
  echo "    Ubuntu: sudo apt install python3.12 python3.12-venv"
  exit 1
fi
PYVER=$(python3 --version)
echo -e "${green}[OK]${reset} $PYVER"

# 2. ffmpeg
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo -e "${yellow}[!] ffmpeg no encontrado${reset}"
  echo "    macOS:  brew install ffmpeg"
  echo "    Ubuntu: sudo apt install ffmpeg"
else
  echo -e "${green}[OK]${reset} $(ffmpeg -version | head -n1)"
fi

# 3. venv
if [ ! -d .venv ]; then
  echo "[*] Creando entorno virtual..."
  python3 -m venv .venv
else
  echo -e "${green}[OK]${reset} .venv ya existe"
fi

# 4. Deps
echo "[*] Instalando dependencias..."
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt

# 5. CUDA? (Linux con NVIDIA)
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || true)
  if [ -n "$GPU" ]; then
    echo ""
    echo -e "${cyan}[i] GPU NVIDIA detectada: $GPU${reset}"
    echo "    Para activar CUDA:"
    echo "       export WHISPER_DEVICE=cuda"
    echo "       export WHISPER_COMPUTE=float16"
  fi
fi

echo ""
echo -e "${green}===================================================${reset}"
echo -e "${green}  INSTALACION COMPLETA${reset}"
echo -e "${green}===================================================${reset}"
echo ""
echo "Para arrancar:"
echo "    source .venv/bin/activate"
echo "    python server.py"
echo ""
echo "Despues abre:  http://localhost:8000"
echo ""
