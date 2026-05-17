"""Voice-to-Text local server (cross-platform).

Uses faster-whisper (CTranslate2). Works on macOS, Windows and Linux.
On Apple Silicon: runs on CPU with int8 (fast enough for large-v3-turbo).
On Windows + NVIDIA: set WHISPER_DEVICE=cuda and WHISPER_COMPUTE=float16.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

# -------- config --------
MODEL_SIZE = os.environ.get("WHISPER_MODEL", "large-v3-turbo")
DEVICE = os.environ.get("WHISPER_DEVICE", "auto")          # auto | cpu | cuda
COMPUTE = os.environ.get("WHISPER_COMPUTE", "default")     # default | int8 | int8_float16 | float16 | float32
CPU_THREADS = int(os.environ.get("WHISPER_CPU_THREADS", "0"))  # 0 = auto

# Whitelist for "auto" detection. If Whisper guesses anything outside this set,
# we fall back to DEFAULT_FALLBACK_LANG. Solves the "audio is bilingüe ca/es but
# Whisper sometimes picks English" problem.
ALLOWED_AUTO_LANGS = set(
    s.strip().lower() for s in os.environ.get("ALLOWED_AUTO_LANGS", "es,ca").split(",") if s.strip()
)
DEFAULT_FALLBACK_LANG = os.environ.get("DEFAULT_FALLBACK_LANG", "es")

# CORS — allow the GitHub Pages frontend to talk to the local server.
# Add more origins via env: ALLOWED_ORIGINS="https://foo.com,https://bar.com"
ALLOWED_ORIGINS = [
    s.strip() for s in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,https://josecl.github.io",
    ).split(",") if s.strip()
]

ROOT = Path(__file__).parent
WEB_DIR = ROOT / "web"
TMP_DIR = ROOT / "tmp"
TMP_DIR.mkdir(exist_ok=True)

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".opus", ".aac", ".wma"}

# -------- model (lazy) --------
_model = None
_model_lock = Lock()
_load_state = {"loaded": False, "loading": False, "error": None, "device": None, "compute": None}
_executor = ThreadPoolExecutor(max_workers=1)


def _resolve_device():
    if DEVICE != "auto":
        return DEVICE, COMPUTE if COMPUTE != "default" else ("float16" if DEVICE == "cuda" else "int8")
    # auto
    try:
        import torch  # noqa: F401
        if hasattr(__import__("torch"), "cuda") and __import__("torch").cuda.is_available():
            return "cuda", "float16" if COMPUTE == "default" else COMPUTE
    except Exception:
        pass
    return "cpu", ("int8" if COMPUTE == "default" else COMPUTE)


def _load_model():
    global _model
    with _model_lock:
        if _model is not None:
            return _model
        _load_state["loading"] = True
        _load_state["error"] = None
        try:
            from faster_whisper import WhisperModel
            dev, comp = _resolve_device()
            _load_state["device"] = dev
            _load_state["compute"] = comp
            kwargs = {"device": dev, "compute_type": comp}
            if CPU_THREADS:
                kwargs["cpu_threads"] = CPU_THREADS
            _model = WhisperModel(MODEL_SIZE, **kwargs)
            _load_state["loaded"] = True
        except Exception as exc:
            _load_state["error"] = repr(exc)
            raise
        finally:
            _load_state["loading"] = False
    return _model


# -------- app --------
app = FastAPI(title="Voice-to-Text · Night City")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/status")
async def status() -> JSONResponse:
    ffmpeg_ok = subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0 \
        if _which("ffmpeg") else False
    return JSONResponse({
        "engine": "faster-whisper",
        "model": MODEL_SIZE,
        "loaded": _load_state["loaded"],
        "loading": _load_state["loading"],
        "device": _load_state["device"],
        "compute": _load_state["compute"],
        "error": _load_state["error"],
        "ffmpeg": ffmpeg_ok,
        "platform": sys.platform,
    })


@app.post("/api/warm")
async def warm() -> JSONResponse:
    """Preload model in background."""
    if _load_state["loaded"] or _load_state["loading"]:
        return JSONResponse({"ok": True, "state": _load_state})
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _load_model)
    return JSONResponse({"ok": True, "state": _load_state})


def _hf_cache_root() -> Path:
    env = os.environ.get("HF_HOME") or os.environ.get("HUGGINGFACE_HUB_CACHE")
    if env:
        return Path(env) / "hub" if (Path(env) / "hub").exists() else Path(env)
    return Path.home() / ".cache" / "huggingface" / "hub"


_MODEL_TOTAL_BYTES = {
    "large-v3-turbo": 1_620_000_000,
    "large-v3": 3_090_000_000,
    "large-v2": 3_090_000_000,
    "medium": 1_530_000_000,
    "small": 484_000_000,
    "base": 145_000_000,
    "tiny": 75_000_000,
}


@app.get("/api/progress")
async def progress() -> JSONResponse:
    """Estimate model download progress by walking the HF cache dir."""
    cache_root = _hf_cache_root()
    bytes_now = 0
    incomplete = []
    matched_dirs: list[str] = []
    if cache_root.exists():
        keyword = MODEL_SIZE.lower().replace(".", "")
        for d in cache_root.glob("models--*"):
            name = d.name.lower()
            if "whisper" in name and keyword in name:
                matched_dirs.append(d.name)
                # Count only real files inside blobs/ (avoid symlinks in snapshots/ that
                # would double-count). HF stores partial downloads as *.incomplete in blobs/.
                blobs = d / "blobs"
                if blobs.exists():
                    for f in blobs.iterdir():
                        try:
                            if f.is_file() and not f.is_symlink():
                                bytes_now += f.stat().st_size
                                if f.name.endswith(".incomplete"):
                                    incomplete.append(f.name)
                        except OSError:
                            pass
    total = _MODEL_TOTAL_BYTES.get(MODEL_SIZE, 1_620_000_000)
    pct = round(min(100.0, (bytes_now / total) * 100), 2) if total else 0
    return JSONResponse({
        "bytes": bytes_now,
        "total_estimated": total,
        "percent": pct,
        "active_downloads": incomplete,
        "matched_dirs": matched_dirs,
        "loaded": _load_state["loaded"],
        "loading": _load_state["loading"],
        "error": _load_state["error"],
    })


def _which(cmd: str) -> bool:
    from shutil import which
    return which(cmd) is not None


async def _extract_audio(src: Path, dst: Path) -> None:
    if not _which("ffmpeg"):
        raise HTTPException(500, "ffmpeg not found in PATH")
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(src),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dst),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HTTPException(500, f"ffmpeg failed: {stderr.decode()[-400:]}")


def _resolve_language(model, audio_path: str, requested: str) -> tuple[str, str]:
    """If requested is a fixed lang, return it. Otherwise auto-detect but
    constrain to ALLOWED_AUTO_LANGS, falling back to DEFAULT_FALLBACK_LANG.

    Returns (effective_language, reason_string).
    """
    if requested and requested != "auto":
        return requested, "user-selected"
    # Sanity check on audio size — empty/tiny WAV → skip detection.
    try:
        size = Path(audio_path).stat().st_size
    except OSError:
        size = 0
    if size < 4096:  # < 4 KB of WAV ≈ < ~0.1s of 16 kHz PCM
        return DEFAULT_FALLBACK_LANG, f"audio too small ({size} B) → fallback"
    try:
        det, prob, _ = model.detect_language(audio_path)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        msg = f"{exc.__class__.__name__}: {exc}"[:120]
        return DEFAULT_FALLBACK_LANG, f"detect-failed ({msg}) → fallback"
    if det in ALLOWED_AUTO_LANGS:
        return det, f"auto-detected '{det}' ({prob*100:.0f}%)"
    return DEFAULT_FALLBACK_LANG, (
        f"detected '{det}' ({prob*100:.0f}%) not in {sorted(ALLOWED_AUTO_LANGS)} → fallback '{DEFAULT_FALLBACK_LANG}'"
    )


def _transcribe_sync(audio_path: str, language: str | None, vad: bool) -> dict:
    model = _load_model()
    eff_lang, reason = _resolve_language(model, audio_path, language or "auto")
    kwargs = {"beam_size": 5, "vad_filter": vad, "language": eff_lang}
    segments_iter, info = model.transcribe(audio_path, **kwargs)
    segments = []
    full_text_parts = []
    for s in segments_iter:
        segments.append({
            "id": s.id,
            "start": float(s.start),
            "end": float(s.end),
            "text": s.text,
        })
        full_text_parts.append(s.text)
    return {
        "text": "".join(full_text_parts).strip(),
        "segments": segments,
        "language": info.language,
        "language_probability": float(info.language_probability),
        "language_reason": reason,
        "duration": float(info.duration),
    }


@app.post("/api/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    vad: bool = Form(True),
) -> JSONResponse:
    started = time.perf_counter()
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in VIDEO_EXTS | AUDIO_EXTS:
        raise HTTPException(400, f"Unsupported file type: {suffix or 'unknown'}")

    with tempfile.TemporaryDirectory(dir=TMP_DIR) as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / f"src{suffix}"
        with src.open("wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        # Normalize anything that's not a clean wav/mp3 to 16k mono WAV
        if suffix in VIDEO_EXTS or suffix in {".m4a", ".opus", ".aac", ".wma", ".flac", ".ogg"}:
            audio = tmp_path / "audio.wav"
            await _extract_audio(src, audio)
        else:
            audio = src

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, _transcribe_sync, str(audio), language, vad,
        )

    return JSONResponse({
        "elapsed_s": round(time.perf_counter() - started, 2),
        "model": MODEL_SIZE,
        "language_requested": language,
        "result": result,
    })


async def _save_upload(file: UploadFile, dst: Path) -> None:
    with dst.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)


def _needs_ffmpeg(suffix: str) -> bool:
    return suffix in VIDEO_EXTS or suffix in {".m4a", ".opus", ".aac", ".wma", ".flac", ".ogg"}


@app.post("/api/transcribe/stream")
async def transcribe_stream(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    vad: bool = Form(True),
):
    """SSE stream: emits meta + segment events as Whisper produces them."""
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in VIDEO_EXTS | AUDIO_EXTS:
        raise HTTPException(400, f"Unsupported file type: {suffix or 'unknown'}")

    tmp = Path(tempfile.mkdtemp(dir=TMP_DIR))
    src = tmp / f"src{suffix}"
    await _save_upload(file, src)

    if _needs_ffmpeg(suffix):
        audio = tmp / "audio.wav"
        await _extract_audio(src, audio)
    else:
        audio = src

    started = time.perf_counter()
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def worker():
        try:
            model = _load_model()
            eff_lang, reason = _resolve_language(model, str(audio), language or "auto")
            kwargs = {"beam_size": 5, "vad_filter": vad, "language": eff_lang}
            segs_iter, info = model.transcribe(str(audio), **kwargs)
            duration = float(info.duration) or 0.001
            loop.call_soon_threadsafe(queue.put_nowait, ("meta", {
                "language": info.language,
                "language_probability": float(info.language_probability),
                "language_reason": reason,
                "language_requested": language,
                "duration": duration,
                "model": MODEL_SIZE,
            }))
            all_text: list[str] = []
            all_segs: list[dict] = []
            for s in segs_iter:
                pct = round(min(100.0, (float(s.end) / duration) * 100), 2)
                seg = {
                    "id": s.id,
                    "start": float(s.start),
                    "end": float(s.end),
                    "text": s.text,
                    "percent": pct,
                }
                all_segs.append(seg)
                all_text.append(s.text)
                loop.call_soon_threadsafe(queue.put_nowait, ("segment", seg))
            loop.call_soon_threadsafe(queue.put_nowait, ("done", {
                "text": "".join(all_text).strip(),
                "segments": all_segs,
                "elapsed_s": round(time.perf_counter() - started, 2),
                "language": info.language,
                "language_reason": reason,
                "duration": duration,
                "model": MODEL_SIZE,
                "language_requested": language,
            }))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", {"error": repr(exc)}))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    _executor.submit(worker)

    async def gen():
        try:
            # Heartbeat-able loop. We rely on the queue but add a small idle timeout
            # so disconnected clients can be detected.
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=20.0)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                if msg is None:
                    break
                ev, data = msg
                yield f"event: {ev}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=os.environ.get("BIND_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )
