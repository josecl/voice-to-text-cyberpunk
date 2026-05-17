# Voice-to-Text · Night City Edition

Transcripción local de audio/vídeo (castellano + català) con interfaz HTML estética *Cyberpunk 2077*. Funciona en **macOS, Windows y Linux** — mismo código.

🌐 **Demo web**: [josecl.github.io/voice-to-text-cyberpunk](https://josecl.github.io/voice-to-text-cyberpunk/) — UI alojada en GitHub Pages que se conecta a **tu** server local (`http://localhost:8000`). Privacidad total: el audio nunca sale de tu equipo.

---

## Stack

- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** (CTranslate2) — motor de Whisper cross-platform
- **Modelo**: `large-v3-turbo` (~1.6 GB, se descarga al primer uso)
- **FastAPI** + **uvicorn** — servidor local
- **ffmpeg** — extracción/normalización de audio
- **HTML/CSS/JS vainilla** — sin frameworks

---

## Requisitos

| Software | Versión | Necesario para |
|---|---|---|
| **git** | Cualquiera reciente | Clonar el repo y recibir actualizaciones |
| **Python** | 3.10 – 3.13 (3.14 puede fallar al compilar CTranslate2) | Backend |
| **ffmpeg** | Cualquiera reciente | Extracción audio de vídeos y normalización |
| **2 GB libres** | en disco | Modelo Whisper |
| **8 GB RAM** | recomendado | Inferencia |

### Instalar las dependencias del sistema

**macOS** (Homebrew):
```bash
brew install git python@3.12 ffmpeg
```

**Windows** (PowerShell + winget):
```powershell
winget install Git.Git Python.Python.3.12 Gyan.FFmpeg -e
# Cierra y vuelve a abrir PowerShell para refrescar el PATH
```

**Debian / Ubuntu**:
```bash
sudo apt install git python3.12 python3.12-venv ffmpeg
```

Verifica:
```bash
git --version
python3 --version   # Windows: python --version
ffmpeg -version
```

---

## Instalación · macOS / Linux

```bash
git clone https://github.com/josecl/voice-to-text-cyberpunk.git
cd voice-to-text-cyberpunk
chmod +x install.sh
./install.sh

# Arrancar
source .venv/bin/activate
python server.py
```

En Apple Silicon corre en CPU con cuantización `int8` (~1.5× real-time con `large-v3-turbo`).

---

## Instalación · Windows

### Setup
```powershell
git clone https://github.com/josecl/voice-to-text-cyberpunk.git
cd voice-to-text-cyberpunk

# Opción rápida — script
powershell -ExecutionPolicy Bypass -File install.ps1

# O paso a paso manualmente
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Si PowerShell bloquea la activación del venv:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### Arrancar
```powershell
.\.venv\Scripts\Activate.ps1
python server.py
```

### GPU NVIDIA (opcional, **muy** recomendable si tienes una)

faster-whisper con CUDA es **5-15× más rápido**. Requisitos:

1. Tarjeta NVIDIA con drivers actualizados
2. [CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads)
3. [cuDNN 9 for CUDA 12](https://developer.nvidia.com/cudnn) (los DLLs deben estar en el PATH)

```powershell
$env:WHISPER_DEVICE = "cuda"
$env:WHISPER_COMPUTE = "float16"
python server.py
```

El HUD mostrará `DEV: CUDA/FLOAT16`. Si falla la inicialización, ves el error en `/api/status` (campo `error`).

---

## Uso

Abre [http://localhost:8000](http://localhost:8000).

1. Pulsa **[ WARM UP ]** en la HUD para precargar el modelo (la primera vez descarga ~1.6 GB)
2. Selecciona idioma: **AUTO (ES/CA) / CASTELLANO / CATALÀ**
3. Arrastra un archivo de audio o vídeo
4. Pulsa **▶ TRANSMIT**
5. Descarga como `.txt` o `.srt`
6. Las transcripciones se guardan automáticamente en `[ HISTORY ]` (localStorage)

---

## Uso desde la demo web (GitHub Pages)

La UI alojada en [josecl.github.io/voice-to-text-cyberpunk](https://josecl.github.io/voice-to-text-cyberpunk/) detecta que no está en `localhost` y hace fetch a `http://localhost:8000` (tu server local). Pasos:

1. Arranca tu server local (`python server.py`)
2. Abre la URL de la demo
3. El banner superior pasa de **[ UNREACHABLE ]** rojo a **[ ONLINE ]** verde

Para apuntar a otro host (p. ej. otro PC de la red): botón `[ BACKEND ]` en HUD o parámetro `?backend=http://192.168.1.50:8000` en la URL.

> ⚠️ Safari es estricto con mixed content (HTTPS → HTTP localhost). Si te falla en Safari, usa la versión local directa (`http://localhost:8000`).

---

## Variables de entorno

| Variable | Default | Notas |
|---|---|---|
| `WHISPER_MODEL` | `large-v3-turbo` | `tiny`, `base`, `small`, `medium`, `large-v3-turbo`, `large-v3` |
| `WHISPER_DEVICE` | `auto` | `auto`, `cpu`, `cuda` |
| `WHISPER_COMPUTE` | `default` (= `int8` en CPU, `float16` en GPU) | También: `int8_float16`, `float32` |
| `WHISPER_CPU_THREADS` | `0` (auto) | Núcleos CPU a usar |
| `ALLOWED_AUTO_LANGS` | `es,ca` | Idiomas a los que se restringe AUTO. Cualquier otra detección cae al fallback |
| `DEFAULT_FALLBACK_LANG` | `es` | Idioma de rescate cuando AUTO detecta algo no permitido |
| `ALLOWED_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000,https://josecl.github.io` | Orígenes CORS permitidos |
| `HF_HOME` | `~/.cache/huggingface` | Dónde se cachea el modelo |

Ejemplo Windows (sesión actual):
```powershell
$env:WHISPER_DEVICE = "cuda"; $env:ALLOWED_AUTO_LANGS = "es,ca,en"; python server.py
```

Persistente:
```powershell
[Environment]::SetEnvironmentVariable("WHISPER_DEVICE", "cuda", "User")
```

---

## Dónde se guarda el modelo (y cómo reutilizarlo)

faster-whisper cachea el modelo en HuggingFace Hub local:

| SO | Ruta |
|---|---|
| macOS / Linux | `~/.cache/huggingface/hub/` |
| Windows | `C:\Users\<TU_USUARIO>\.cache\huggingface\hub\` |

La carpeta del modelo es `models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/`. **Cópiala entera** entre máquinas para evitar redescargar 1.6 GB.

Con tar para preservar symlinks:
```bash
# Origen
cd ~/.cache/huggingface/hub
tar czhf whisper-turbo.tgz models--mobiuslabsgmbh--faster-whisper-large-v3-turbo

# Destino: descomprimir en la ruta equivalente (7-Zip soporta tar.gz en Windows)
```

Alternativa: define `HF_HOME` apuntando a una carpeta que ya tenga el cache:
```powershell
$env:HF_HOME = "D:\modelos\hf"
```

---

## Verificar que funciona

```bash
# 1. ¿Server arriba?
curl http://localhost:8000/api/status

# 2. ¿Modelo cacheado?
curl http://localhost:8000/api/progress
# "percent" cerca de 100 si ya está descargado
```

En la web: `[ WARM UP ]` → barra amarilla → `[ READY ]` verde en el HUD.

---

## Troubleshooting

| Síntoma | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: faster_whisper` | venv no activado | `.\.venv\Scripts\Activate.ps1` (Win) / `source .venv/bin/activate` (Unix) |
| `RuntimeError: Library cudnn_ops_infer64_8.dll is not found` | falta cuDNN | Instala cuDNN 9 y añade los DLLs al PATH |
| Modelo se queda en `LOADING INTO MEMORY` y no avanza | Primera vez: está descargando 1.6 GB | Mira `/api/progress` para ver bytes |
| HUD: `FFMPEG: MISSING` | ffmpeg no está en PATH | Reinstala con `winget` / `brew` y abre terminal nueva |
| `AUTO` detecta inglés | Audio ambiguo en los primeros 30 s | El whitelist (`ALLOWED_AUTO_LANGS=es,ca`) ya lo redirige a `es`. Para permitir más idiomas: `ALLOWED_AUTO_LANGS=es,ca,en` |
| Puerto 8000 ocupado | Otro proceso | Edita el `port=8000` final de `server.py` o mata el otro proceso |
| Pip falla compilando ctranslate2 | Python demasiado nuevo (3.14) | Instala Python 3.12 y rehaz el venv |
| Demo web no conecta al server local | CORS o mixed content | Verifica que `python server.py` está corriendo y que el botón `[ BACKEND ]` apunta a `http://localhost:8000` |

---

## Ejecutar como servicio (opcional)

### Windows · Task Scheduler
- Programa: `C:\ruta\voice-to-text-cyberpunk\.venv\Scripts\python.exe`
- Argumentos: `server.py`
- Directorio: `C:\ruta\voice-to-text-cyberpunk`
- Disparador: *Al iniciar sesión*

### macOS · launchd
Crea `~/Library/LaunchAgents/com.local.voicetotext.plist` con tu ruta al venv apuntando a `server.py`.

### Linux · systemd
Unit en `~/.config/systemd/user/voicetotext.service` con `ExecStart=/ruta/.venv/bin/python /ruta/server.py`, luego `systemctl --user enable --now voicetotext`.

---

## Acceso desde otros equipos de la red local

Por defecto el server escucha solo en `127.0.0.1`. Para exponerlo en LAN, edita la última línea de `server.py`:

```python
uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
```

⚠️ No expongas a internet sin autenticación — no hay auth implementada.

---

## Notas técnicas

- El vídeo se convierte a WAV 16 kHz mono con `ffmpeg` antes de transcribir
- Los uploads viven en `tmp/` y se borran al terminar cada request
- `vad_filter` (Silero VAD) está activado: ignora silencios → más rápido y limpio
- El historial vive en `localStorage` del navegador (límite ~5 MB, FIFO con tope de 50 entradas)
- La transcripción se hace en **streaming**: el texto aparece conforme Whisper lo emite, no espera al final
