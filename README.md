# Voice-to-Text · Night City Edition

Transcripción local de audio/vídeo (castellano + català) con interfaz HTML estética *Cyberpunk 2077*. Funciona en **macOS, Windows y Linux** — mismo código.

🌐 **Demo web**: [josecl.github.io/voice-to-text-cyberpunk](https://josecl.github.io/voice-to-text-cyberpunk/) — UI alojada en GitHub Pages que se conecta a **tu** server local (`http://localhost:8000`). Privacidad total: el audio nunca sale de tu equipo.

## Stack

- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** (CTranslate2) — motor de Whisper cross-platform
- **Modelo**: `large-v3-turbo` (~1.6 GB, se descarga al primer uso)
- **FastAPI** + **uvicorn** — servidor local
- **ffmpeg** — extracción/normalización de audio
- **HTML/CSS/JS vainilla** — sin frameworks

## Requisitos comunes

- Python 3.10+
- ffmpeg en el PATH
- ~2 GB libres para el modelo

## Instalación · macOS

```bash
brew install ffmpeg   # ya instalado en tu caso
cd /Users/jose/desa/voice-to-text
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

En Mac (Apple Silicon o Intel) corre en CPU con cuantización `int8` por defecto. `large-v3-turbo` es ~4-8× más rápido que `large-v3` con calidad muy similar.

## Instalación · Windows

### Opción A — CPU (cualquier PC)

```powershell
# 1. Instalar ffmpeg (una vez)
winget install Gyan.FFmpeg
# o:  choco install ffmpeg

# 2. Clonar/copiar el proyecto y entrar
cd C:\ruta\voice-to-text

# 3. Crear venv e instalar
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 4. Arrancar
python server.py
```

### Opción B — GPU NVIDIA (mucho más rápido)

Requiere **CUDA 12** y **cuDNN 9** instalados (CTranslate2 ≥ 4.5 los usa). Guía rápida:

1. Instala los runtimes:
   - [CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads)
   - [cuDNN 9.x for CUDA 12](https://developer.nvidia.com/cudnn)
2. Asegúrate de que los DLL están en el PATH (instalador suele añadirlos)
3. Define variables de entorno antes de arrancar:

```powershell
$env:WHISPER_DEVICE = "cuda"
$env:WHISPER_COMPUTE = "float16"
python server.py
```

## Uso

Abre [http://localhost:8000](http://localhost:8000).

1. Pulsa **[ WARM UP ]** en la HUD para precargar el modelo (la primera vez descarga ~1.6 GB)
2. Selecciona idioma: **AUTO / CASTELLANO / CATALÀ**
3. Arrastra un archivo de audio o vídeo
4. Pulsa **▶ TRANSMIT**
5. Descarga como `.txt` o `.srt`

## Variables de entorno

| Variable | Default | Notas |
|---|---|---|
| `WHISPER_MODEL` | `large-v3-turbo` | También: `large-v3`, `medium`, `small`, `base`, `tiny` |
| `WHISPER_DEVICE` | `auto` | `auto` / `cpu` / `cuda` |
| `WHISPER_COMPUTE` | `default` | `int8` (CPU) / `float16` / `int8_float16` (GPU) / `float32` |
| `WHISPER_CPU_THREADS` | `0` (auto) | Número de threads CPU |

## Dónde se guarda el modelo

faster-whisper usa la caché de HuggingFace:
- macOS/Linux: `~/.cache/huggingface/hub/`
- Windows: `C:\Users\<tu_usuario>\.cache\huggingface\hub\`

Puedes copiarlo entre máquinas para evitar descargar dos veces.

## Notas

- El vídeo se convierte a WAV 16 kHz mono con `ffmpeg` antes de transcribir
- Los uploads viven en `tmp/` y se borran al terminar cada request
- `vad_filter` (Silero VAD) está activado: ignora silencios → más rápido y limpio
