# Instalación — Voice-to-Text · Night City

Guía para reproducir el proyecto en **otro equipo**, especialmente **Windows PC**. También cubre macOS y Linux por completitud.

---

## 0. Qué transferir desde este Mac

El proyecto vive en `/Users/jose/desa/voice-to-text/`. Lo que necesitas copiar al otro equipo:

```
voice-to-text/
├── server.py
├── web/index.html
├── requirements.txt
├── install.ps1          ← Windows
├── install.sh           ← macOS / Linux
├── README.md
└── INSTALL.md           (este archivo)
```

**NO copies** (se regeneran solos):
- `.venv/` — entorno Python específico de cada SO
- `tmp/` — uploads temporales
- `__pycache__/` — bytecode Python
- `.DS_Store`

### Cómo transferir

Tres opciones, de más simple a más sostenible:

| Opción | Cuándo | Cómo |
|---|---|---|
| **Zip + USB / mail / Drive** | Una sola vez | `cd /Users/jose/desa && zip -r voice-to-text.zip voice-to-text -x "*/.venv/*" -x "*/tmp/*" -x "*/__pycache__/*" -x "*.DS_Store"` |
| **Git** | Vas a iterar | `cd voice-to-text && git init && git add . && git commit -m "init"` → push a GitHub privado → `git clone` en Windows |
| **rsync (mismo wifi)** | Mac → Linux | `rsync -av --exclude .venv --exclude tmp --exclude __pycache__ voice-to-text/ user@host:~/voice-to-text/` |

---

## 1. Pre-requisitos comunes

| Software | Versión | Necesario para |
|---|---|---|
| **Python** | 3.10 – 3.12 (3.13 ok, 3.14 puede dar problemas con CTranslate2) | Backend |
| **ffmpeg** | Cualquiera reciente | Extracción audio de vídeos |
| **2 GB libres** | en disco | Modelo Whisper |
| **8 GB RAM** | recomendado | Inferencia |

---

## 2. Instalación · Windows

### 2.1 Instalar Python y ffmpeg (una sola vez)

Abre **PowerShell** y ejecuta:

```powershell
# Python 3.12 (si no lo tienes)
winget install Python.Python.3.12 -e

# ffmpeg
winget install Gyan.FFmpeg -e

# Cierra y vuelve a abrir PowerShell para que el PATH se refresque
```

Alternativa con [Chocolatey](https://chocolatey.org/):
```powershell
choco install python312 ffmpeg -y
```

Verifica:
```powershell
python --version    # → Python 3.12.x
ffmpeg -version     # → ffmpeg version ...
```

### 2.2 Setup del proyecto

```powershell
# Clona el repo (o descomprime el zip si te lo pasaron por otra vía)
git clone https://github.com/josecl/voice-to-text-cyberpunk.git
cd voice-to-text-cyberpunk

# Opción rápida: ejecutar el script
powershell -ExecutionPolicy Bypass -File install.ps1

# O paso a paso manualmente:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Si PowerShell bloquea la activación del venv, ejecuta una vez:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### 2.3 Arrancar

```powershell
.\.venv\Scripts\Activate.ps1
python server.py
```

Abre [http://localhost:8000](http://localhost:8000). Pulsa `[ WARM UP ]` — la primera vez descarga ~1.6 GB del modelo.

### 2.4 GPU NVIDIA (opcional, **muy** recomendable si tienes una)

faster-whisper con CUDA es **5-15× más rápido**. Requisitos:

1. Tarjeta NVIDIA con drivers actualizados
2. [CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads)
3. [cuDNN 9 para CUDA 12](https://developer.nvidia.com/cudnn) (extraer DLLs al PATH o junto al ejecutable Python)

Define variables y arranca:

```powershell
$env:WHISPER_DEVICE = "cuda"
$env:WHISPER_COMPUTE = "float16"
python server.py
```

El HUD mostrará `DEV: CUDA/FLOAT16`. Si fallara la inicialización, ves el error en `/api/status` (campo `error`).

---

## 3. Instalación · macOS / Linux

```bash
# macOS
brew install python@3.12 ffmpeg

# Debian/Ubuntu
sudo apt install python3.12 python3.12-venv ffmpeg

# Setup
cd voice-to-text
chmod +x install.sh
./install.sh

# Arrancar
source .venv/bin/activate
python server.py
```

En Apple Silicon corre en CPU con `int8`. Suficientemente rápido (≈1.5× real time para `large-v3-turbo`).

---

## 4. Reutilizar el modelo (evitar re-descarga de 1.6 GB)

faster-whisper cachea el modelo en HuggingFace Hub local:

| SO | Ruta |
|---|---|
| macOS / Linux | `~/.cache/huggingface/hub/` |
| Windows | `C:\Users\<TU_USUARIO>\.cache\huggingface\hub\` |

La carpeta del modelo es `models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/`. **Cópiala entera** del Mac al PC en la ruta equivalente, y el primer `WARM UP` será instantáneo.

Con tar para no perder symlinks:
```bash
# en el Mac
cd ~/.cache/huggingface/hub
tar czhf whisper-turbo.tgz models--mobiuslabsgmbh--faster-whisper-large-v3-turbo

# en el PC, dejarlo en C:\Users\<user>\.cache\huggingface\hub\
# y descomprimir (7-Zip soporta tar.gz)
```

Alternativa: en Windows define `HF_HOME` apuntando a una carpeta donde ya tengas el cache:
```powershell
$env:HF_HOME = "D:\modelos\hf"
```

---

## 5. Variables de entorno (opcional)

| Variable | Default | Notas |
|---|---|---|
| `WHISPER_MODEL` | `large-v3-turbo` | `tiny`, `base`, `small`, `medium`, `large-v3-turbo`, `large-v3` |
| `WHISPER_DEVICE` | `auto` | `auto`, `cpu`, `cuda` |
| `WHISPER_COMPUTE` | `default` (= `int8` en CPU, `float16` en GPU) | También: `int8_float16`, `float32` |
| `WHISPER_CPU_THREADS` | `0` (auto) | Núcleos CPU a usar |
| `ALLOWED_AUTO_LANGS` | `es,ca` | Idiomas a los que se restringe AUTO. Cualquier otra detección cae al fallback |
| `DEFAULT_FALLBACK_LANG` | `es` | Idioma de rescate cuando AUTO detecta algo no permitido |
| `HF_HOME` | `~/.cache/huggingface` | Dónde se cachea el modelo |

Ejemplo Windows (sesión actual):
```powershell
$env:WHISPER_DEVICE = "cuda"; $env:ALLOWED_AUTO_LANGS = "es,ca,en"; python server.py
```

Para hacerlo persistente:
```powershell
[Environment]::SetEnvironmentVariable("WHISPER_DEVICE", "cuda", "User")
```

---

## 6. Verificar que funciona

```powershell
# 1. ¿Server arriba?
curl http://localhost:8000/api/status

# 2. ¿Detecta ffmpeg?
# La respuesta debe traer "ffmpeg": true

# 3. ¿Modelo cacheado?
curl http://localhost:8000/api/progress
# "percent" cerca de 100 si ya está descargado
```

En la web: `[ WARM UP ]` → barra amarilla → `[ READY ]` verde en el HUD.

---

## 7. Troubleshooting

| Síntoma | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: faster_whisper` | venv no activado | `.\.venv\Scripts\Activate.ps1` (Win) / `source .venv/bin/activate` (Unix) |
| `RuntimeError: Library cudnn_ops_infer64_8.dll is not found` | falta cuDNN | Instalar cuDNN 9 y poner DLLs en PATH |
| Modelo se queda en `LOADING INTO MEMORY` y no avanza | Primera vez: está descargando 1.6 GB. Tiene paciencia, o mira `/api/progress` |
| HUD: `FFMPEG: MISSING` | ffmpeg no está en PATH | Reinstala con `winget` y abre PowerShell nueva |
| `AUTO` detecta inglés | Audio ambiguo en primeros 30s | El whitelist (`ALLOWED_AUTO_LANGS=es,ca`) ya lo redirige a `es`. Si quieres permitir más idiomas, edita la variable |
| Puerto 8000 ocupado | Otra app | `python server.py` y edita el `port=8000` final, o mata el otro proceso |
| Pip falla compilando ctranslate2 | Python demasiado nuevo (3.14) | Instala Python 3.12 y rehaz el venv |

---

## 8. Ejecutar como servicio (opcional)

### Windows — Task Scheduler

Crea tarea que se ejecute al iniciar sesión:
- Programa: `C:\ruta\voice-to-text\.venv\Scripts\python.exe`
- Argumentos: `server.py`
- Directorio: `C:\ruta\voice-to-text`

### macOS — launchd

Plantilla `~/Library/LaunchAgents/com.local.voicetotext.plist` (te lo monto si lo pides).

---

## 9. Acceso desde otros equipos de la red local

Por defecto el server escucha solo en `127.0.0.1` (solo el equipo). Para exponerlo en LAN, edita la última línea de `server.py`:

```python
uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
```

⚠️ No expongas a internet sin autenticación — no hay auth implementada.
