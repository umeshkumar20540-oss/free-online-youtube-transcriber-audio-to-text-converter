"""
FastAPI application backend for WhisperFlow YouTube Transcriber.
Provides SSE streaming, REST endpoints, history database management, and export downloads.
"""

import os
import sys
import json
import uuid
import time
import asyncio
import logging
import threading
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from ffmpeg_utils import ensure_ffmpeg_on_path
from downloader import get_video_info, download_youtube_audio, prepare_local_audio, is_valid_youtube_url
from transcriber import WhisperEngine
from storage import init_db, save_transcription, list_transcriptions, get_transcription, delete_transcription
from summarizer import generate_offline_summary
import exporters

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("app")

# Ensure environment & paths
ensure_ffmpeg_on_path()
init_db()

app = FastAPI(title=config.APP_TITLE, version=config.APP_VERSION)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = config.BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class JobState:
    """Maintains sequential event history and client subscriber queues for auto-reconnect."""
    def __init__(self, job_id: str, request_data: dict):
        self.job_id = job_id
        self.request_data = request_data
        self.status = "running"  # "running", "completed", "error"
        self.events: List[Dict[str, Any]] = []
        self.subscribers: List[asyncio.Queue] = []
        self.completed_result: Optional[dict] = None
        self.error_message: Optional[str] = None
        self.created_at = time.time()
        self.updated_at = time.time()
        self.lock = threading.Lock()

    def add_event(self, event_data: dict, loop: asyncio.AbstractEventLoop):
        with self.lock:
            event_id = len(self.events)
            event_data["event_id"] = event_id
            self.events.append(event_data)
            self.updated_at = time.time()
            if event_data.get("type") == "completed":
                self.status = "completed"
                self.completed_result = event_data
            elif event_data.get("type") == "error":
                self.status = "error"
                self.error_message = event_data.get("error")

            for q in list(self.subscribers):
                try:
                    asyncio.run_coroutine_threadsafe(q.put(event_data), loop)
                except Exception:
                    pass

    def get_events_since(self, last_event_id: int) -> List[Dict[str, Any]]:
        with self.lock:
            if last_event_id < 0:
                return list(self.events)
            start_idx = last_event_id + 1
            if start_idx < len(self.events):
                return list(self.events[start_idx:])
            return []


# Active jobs mapping: job_id -> JobState
active_jobs: Dict[str, JobState] = {}
jobs_lock = threading.Lock()



# Models for Request Bodies
class TranscribeRequest(BaseModel):
    url: Optional[str] = None
    file_id: Optional[str] = None
    model_size: str = config.DEFAULT_MODEL
    language: str = "auto"
    task: str = "transcribe"
    vad_filter: bool = True
    word_timestamps: bool = True
    initial_prompt: Optional[str] = None
    device: str = "auto"


class UrlInfoRequest(BaseModel):
    url: str


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = config.BASE_DIR / "templates" / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index template not found.")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get("/api/hardware")
async def get_hardware():
    """Returns detected GPU / CPU capabilities."""
    return config.detect_hardware()


@app.get("/api/models")
async def get_models():
    """Returns list and metadata of supported Whisper models."""
    return {
        "models": config.AVAILABLE_MODELS,
        "default": config.DEFAULT_MODEL
    }


@app.get("/api/languages")
async def get_languages():
    """Returns list of supported languages."""
    return config.SUPPORTED_LANGUAGES


@app.post("/api/info")
async def fetch_url_info(req: UrlInfoRequest):
    """Fetches YouTube video metadata without downloading audio."""
    if not req.url or not is_valid_youtube_url(req.url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL.")
    try:
        info = get_video_info(req.url)
        return info
    except Exception as e:
        logger.error(f"Error fetching video info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio")
async def download_audio_for_browser(req: UrlInfoRequest):
    """Downloads compact AAC audio locally on the user's PC and streams it to the browser UI."""
    if not req.url or not is_valid_youtube_url(req.url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL.")
    try:
        from urllib.parse import quote
        info = download_youtube_audio(req.url)
        audio_path = Path(info["audio_path"])
        ext = audio_path.suffix.lower()
        media_type = "audio/mp4" if ext in [".m4a", ".mp4", ".aac"] else "audio/mpeg"
        return FileResponse(
            path=str(audio_path),
            media_type=media_type,
            filename=audio_path.name,
            headers={
                "X-Audio-Duration": str(info.get("duration", 0)),
                "X-Audio-Title": quote(str(info.get("title", "audio"))[:100]),
                "X-Audio-Uploader": quote(str(info.get("uploader", ""))[:100]),
                "Access-Control-Expose-Headers": "X-Audio-Duration, X-Audio-Title, X-Audio-Uploader, Content-Length",
            },
        )
    except Exception as e:
        logger.error(f"Error extracting local audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_audio_file(file: UploadFile = File(...)):
    """Uploads a local audio or video file for transcription."""
    file_id = f"local_{uuid.uuid4().hex[:10]}"
    ext = Path(file.filename or "audio.mp3").suffix or ".mp3"
    saved_path = config.AUDIO_CACHE_DIR / f"{file_id}{ext}"

    try:
        content = await file.read()
        with open(saved_path, "wb") as f:
            f.write(content)

        meta = prepare_local_audio(saved_path)
        meta["id"] = file_id
        meta["title"] = file.filename or "Local File"
        return meta
    except Exception as e:
        logger.error(f"Error handling upload: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


def run_transcription_job(job_id: str, req: TranscribeRequest, loop: asyncio.AbstractEventLoop):
    """Synchronous worker thread that executes download + Faster-Whisper transcription."""
    def push_event(data: dict):
        with jobs_lock:
            job = active_jobs.get(job_id)
        if job:
            job.add_event(data, loop)

    try:
        # Step 1: Ingestion
        if req.url:
            push_event({
                "type": "status",
                "stage": "downloading",
                "message": "Connecting to YouTube and extracting audio stream...",
                "progress": 5.0
            })

            def download_progress(pct, speed, eta):
                # Download progress mapped to 5% - 25%
                mapped_pct = 5.0 + (pct * 0.20)
                push_event({
                    "type": "status",
                    "stage": "downloading",
                    "message": f"Downloading audio: {pct:.0f}% ({speed}, ETA {eta})",
                    "progress": round(mapped_pct, 1)
                })

            media_info = download_youtube_audio(
                url=req.url,
                progress_callback=download_progress
            )
            audio_path = media_info["audio_path"]
            source_type = "youtube"
            webpage_url = req.url
        elif req.file_id:
            push_event({
                "type": "status",
                "stage": "preparing",
                "message": "Preparing uploaded local audio file...",
                "progress": 20.0
            })
            candidates = list(config.AUDIO_CACHE_DIR.glob(f"{req.file_id}*"))
            if not candidates:
                raise FileNotFoundError("Uploaded audio file not found on server.")
            audio_path = str(candidates[0].resolve())
            media_info = prepare_local_audio(candidates[0])
            source_type = "upload"
            webpage_url = ""
        else:
            raise ValueError("Neither YouTube URL nor local file_id provided.")

        # Step 2: Faster-Whisper Model Loading
        push_event({
            "type": "status",
            "stage": "loading_model",
            "message": f"Loading Faster-Whisper '{req.model_size}' model...",
            "progress": 25.0
        })

        engine = WhisperEngine.get_instance()

        push_event({
            "type": "status",
            "stage": "transcribing",
            "message": "Transcribing audio with Faster-Whisper...",
            "progress": 30.0
        })

        # Step 3: Transcription Streaming
        stream = engine.transcribe_stream(
            audio_path=audio_path,
            model_size=req.model_size,
            language=req.language,
            task=req.task,
            vad_filter=req.vad_filter,
            word_timestamps=req.word_timestamps,
            initial_prompt=req.initial_prompt,
            device=req.device
        )

        completed_result = None

        for item in stream:
            if item["type"] == "info":
                push_event({
                    "type": "meta",
                    "detected_language": item["detected_language"],
                    "language_probability": item["language_probability"],
                    "duration": item["duration"],
                    "device_used": item["device_used"],
                    "compute_type": item["compute_type"],
                    "video_title": media_info.get("title", ""),
                    "uploader": media_info.get("uploader", ""),
                    "thumbnail": media_info.get("thumbnail", ""),
                    "audio_filename": Path(audio_path).name,
                })
            elif item["type"] == "segment":
                # Transcription progress mapped between 30% and 95%
                mapped_prog = 30.0 + (item["progress"] * 0.65)
                push_event({
                    "type": "segment",
                    "segment": item["segment"],
                    "progress": round(mapped_prog, 1),
                    "current_time": item["current_time"],
                    "total_time": item["total_time"]
                })
            elif item["type"] == "completed":
                completed_result = item

        if not completed_result:
            raise RuntimeError("Transcription completed without returning output.")

        # Step 4: Summary Generation
        push_event({
            "type": "status",
            "stage": "summarizing",
            "message": "Generating key takeaways and chapter markers...",
            "progress": 96.0
        })

        summary_text = generate_offline_summary(
            completed_result["full_text"],
            completed_result["segments"]
        )

        # Step 5: Save to SQLite History
        record = {
            "id": media_info.get("id") or str(uuid.uuid4())[:10],
            "title": media_info.get("title", "Untitled Audio"),
            "uploader": media_info.get("uploader", "Unknown"),
            "source_type": source_type,
            "url": webpage_url,
            "duration": media_info.get("duration", completed_result["duration"]),
            "thumbnail": media_info.get("thumbnail", ""),
            "model_used": req.model_size,
            "language": completed_result["detected_language"],
            "full_text": completed_result["full_text"],
            "segments": completed_result["segments"],
            "audio_path": audio_path,
            "summary": summary_text,
        }
        saved_id = save_transcription(record)

        # Step 6: Done!
        push_event({
            "type": "completed",
            "progress": 100.0,
            "record_id": saved_id,
            "title": record["title"],
            "uploader": record["uploader"],
            "duration": record["duration"],
            "thumbnail": record["thumbnail"],
            "language": record["language"],
            "full_text": record["full_text"],
            "segments": record["segments"],
            "summary": record["summary"],
            "audio_filename": Path(audio_path).name,
            "model_used": req.model_size,
            "device_used": completed_result.get("device_used", "cpu"),
            "compute_type": completed_result.get("compute_type", "int8")
        })

    except Exception as e:
        logger.exception("Error in transcription job")
        push_event({
            "type": "error",
            "error": str(e)
        })


@app.post("/api/transcribe")
async def start_transcription(req: TranscribeRequest):
    """Initiates a transcription job and returns its job ID for SSE streaming."""
    if not req.url and not req.file_id:
        raise HTTPException(status_code=400, detail="Either 'url' or 'file_id' must be specified.")

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    loop = asyncio.get_running_loop()

    with jobs_lock:
        active_jobs[job_id] = JobState(job_id, req.dict())

    thread = threading.Thread(
        target=run_transcription_job,
        args=(job_id, req, loop),
        daemon=True
    )
    thread.start()

    return {"job_id": job_id}


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Returns current status and event count for a job to enable client state resumption."""
    with jobs_lock:
        job = active_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "last_event_id": len(job.events) - 1,
        "total_events": len(job.events),
        "completed_result": job.completed_result,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }


@app.get("/api/active_job")
async def get_active_job():
    """Returns the most recent active or running job, if any."""
    with jobs_lock:
        for j_id, j in reversed(list(active_jobs.items())):
            if j.status == "running":
                return {
                    "job_id": j_id,
                    "status": "running",
                    "last_event_id": len(j.events) - 1
                }
        now = time.time()
        for j_id, j in reversed(list(active_jobs.items())):
            if now - j.updated_at < 300:
                return {
                    "job_id": j_id,
                    "status": j.status,
                    "last_event_id": len(j.events) - 1
                }
    return {"job_id": None}


@app.get("/api/stream/{job_id}")
async def stream_job_events(job_id: str, last_event_id: int = Query(-1)):
    """SSE endpoint delivering live transcription updates with event replay and auto-reconnect."""
    with jobs_lock:
        job = active_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription job not found.")

    client_queue = asyncio.Queue()
    with job.lock:
        job.subscribers.append(client_queue)

    async def event_generator():
        try:
            # 1. Replay missed events from last_event_id + 1
            missed = job.get_events_since(last_event_id)
            for evt in missed:
                yield f"id: {evt['event_id']}\ndata: {json.dumps(evt, ensure_ascii=False)}\n\n"
                if evt.get("type") in ("completed", "error"):
                    return

            if job.status in ("completed", "error"):
                return

            # 2. Stream new live events as they arrive
            while True:
                data = await client_queue.get()
                yield f"id: {data['event_id']}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                if data.get("type") in ("completed", "error"):
                    break
        finally:
            with job.lock:
                if client_queue in job.subscribers:
                    job.subscribers.remove(client_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/history")
async def get_history(q: Optional[str] = Query(None)):
    """Returns past transcriptions with optional search query."""
    return list_transcriptions(search_query=q)


@app.get("/api/history/{record_id}")
async def get_history_detail(record_id: str):
    """Retrieves full details for a past transcription."""
    item = get_transcription(record_id)
    if not item:
        raise HTTPException(status_code=404, detail="Transcription not found.")
    
    # Check if audio file still exists and attach filename
    if item.get("audio_path") and os.path.exists(item["audio_path"]):
        item["audio_filename"] = Path(item["audio_path"]).name
    else:
        item["audio_filename"] = None

    return item


@app.delete("/api/history/{record_id}")
async def remove_history_record(record_id: str):
    """Deletes a transcription record."""
    success = delete_transcription(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transcription record not found.")
    return {"status": "success", "id": record_id}


@app.get("/api/export/{record_id}/{fmt}")
async def export_transcript(record_id: str, fmt: str):
    """Generates and downloads exported transcript in requested format."""
    record = get_transcription(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Transcription record not found.")

    fmt = fmt.lower()
    title_slug = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in record.get("title", "transcript"))[:40]

    segments = record.get("segments", [])

    if fmt == "txt":
        content = exporters.export_txt(segments, with_timestamps=True)
        media_type = "text/plain; charset=utf-8"
        filename = f"{title_slug}.txt"
    elif fmt == "raw_txt":
        content = exporters.export_txt(segments, with_timestamps=False)
        media_type = "text/plain; charset=utf-8"
        filename = f"{title_slug}_raw.txt"
    elif fmt == "srt":
        content = exporters.export_srt(segments)
        media_type = "application/x-subrip; charset=utf-8"
        filename = f"{title_slug}.srt"
    elif fmt == "vtt":
        content = exporters.export_vtt(segments)
        media_type = "text/vtt; charset=utf-8"
        filename = f"{title_slug}.vtt"
    elif fmt == "json":
        content = exporters.export_json(record)
        media_type = "application/json; charset=utf-8"
        filename = f"{title_slug}.json"
    elif fmt == "csv":
        content = exporters.export_csv(segments)
        media_type = "text/csv; charset=utf-8"
        filename = f"{title_slug}.csv"
    elif fmt == "md":
        content = exporters.export_markdown(record)
        media_type = "text/markdown; charset=utf-8"
        filename = f"{title_slug}.md"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {fmt}")

    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/audio/{filename}")
async def stream_audio(filename: str):
    """Streams audio file with HTTP Range support for synchronized browser playback."""
    file_path = config.AUDIO_CACHE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")

    # Determine media type
    ext = file_path.suffix.lower()
    media_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".flac": "audio/flac"
    }
    media_type = media_map.get(ext, "audio/mpeg")
    return FileResponse(path=str(file_path), media_type=media_type)


def start_server():
    """CLI / launcher entry point."""
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="WhisperFlow YouTube Transcriber")
    parser.add_argument("--host", default=config.APP_HOST, help="Host to bind")
    parser.add_argument("--port", type=int, default=config.APP_PORT, help="Port to bind")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    logger.info(f"Starting {config.APP_TITLE} on {url}")

    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    start_server()
