"""
Audio downloader and YouTube ingestion module using yt-dlp and ffmpeg.
"""

import os
import re
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable

import yt_dlp

from ffmpeg_utils import get_ffmpeg_path
from config import AUDIO_CACHE_DIR

logger = logging.getLogger(__name__)


def format_duration(seconds: Optional[float]) -> str:
    """Formats seconds into HH:MM:SS or MM:SS."""
    if not seconds or seconds < 0:
        return "00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def is_valid_youtube_url(url: str) -> bool:
    """
    Checks if an input string is a valid YouTube link, media URL, or local file.
    Permissive to all YouTube share formats (live, shorts, mobile, timestamps, embed).
    """
    u = url.strip()
    if not u:
        return False
    # If it's a local file that exists
    if os.path.exists(u):
        return True
    # YouTube domains
    if "youtube.com" in u.lower() or "youtu.be" in u.lower():
        return True
    # Any generic web media URL
    if u.startswith("http://") or u.startswith("https://"):
        return True
    return False


def get_video_info(url: str) -> Dict[str, Any]:
    """
    Fetches video metadata quickly without downloading the full audio stream.
    Optimized for fast preview (~1-2 seconds) with fallback for local files.
    """
    u = url.strip()

    # Local file path handling
    if os.path.exists(u):
        return prepare_local_audio(Path(u))

    ffmpeg_exe = get_ffmpeg_path()
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "noplaylist": True,
        "socket_timeout": 15,
        "ffmpeg_location": ffmpeg_exe,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(u, download=False)
            if not info:
                raise ValueError("Could not retrieve media information.")

            if "entries" in info and info["entries"]:
                info = info["entries"][0]

            duration = info.get("duration")
            return {
                "id": info.get("id", str(uuid.uuid4())[:8]),
                "title": info.get("title", "Unknown Title"),
                "uploader": info.get("uploader") or info.get("channel") or "Unknown Channel",
                "duration": duration or 0,
                "duration_formatted": format_duration(duration),
                "thumbnail": info.get("thumbnail") or "",
                "view_count": info.get("view_count", 0),
                "webpage_url": info.get("webpage_url", u),
            }
        except Exception as e:
            logger.error(f"Failed to fetch video info: {e}")
            raise RuntimeError(f"Error fetching media details: {str(e)}")


def download_youtube_audio(
    url: str,
    output_dir: Optional[Path] = None,
    progress_callback: Optional[Callable[[float, str, str], None]] = None
) -> Dict[str, Any]:
    """
    Downloads the audio stream from a YouTube video or web URL and converts it to MP3.
    Calls progress_callback(percentage, speed_str, eta_str) during download.
    """
    u = url.strip()
    if output_dir is None:
        output_dir = AUDIO_CACHE_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Local file check
    if os.path.exists(u):
        return prepare_local_audio(Path(u))

    ffmpeg_exe = get_ffmpeg_path()
    video_id = str(uuid.uuid4())[:12]

    def ytdl_hook(d):
        if progress_callback and d.get("status") == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            percent = (downloaded / total_bytes * 100.0) if total_bytes > 0 else 0.0

            speed = d.get("speed")
            speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "N/A"
            eta = d.get("eta")
            eta_str = f"{eta}s" if eta else "calculating..."

            progress_callback(percent, speed_str, eta_str)

    ydl_opts = {
        "format": "ba[abr<=64][ext=m4a]/139/ba[ext=m4a]/140/ba/b",
        "outtmpl": str(output_dir / f"%(id)s.%(ext)s"),
        "noplaylist": True,
        "concurrent_fragment_downloads": 8,
        "resize_buffer": True,
        "socket_timeout": 30,
        "ffmpeg_location": ffmpeg_exe,
        "progress_hooks": [ytdl_hook],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info:
            info = info["entries"][0]

        real_id = info.get("id", video_id)
        # Expected output path after postprocessing
        expected_audio_path = output_dir / f"{real_id}.mp3"

        if not expected_audio_path.exists():
            # Check for alternative audio extensions
            candidates = list(output_dir.glob(f"{real_id}.*"))
            if candidates:
                expected_audio_path = candidates[0]
            else:
                raise FileNotFoundError(f"Audio file was not generated for {url}")

        duration = info.get("duration")
        return {
            "id": real_id,
            "title": info.get("title", "Untitled Audio"),
            "uploader": info.get("uploader") or info.get("channel", "Unknown"),
            "duration": duration or 0,
            "duration_formatted": format_duration(duration),
            "thumbnail": info.get("thumbnail", ""),
            "audio_path": str(expected_audio_path.resolve()),
            "webpage_url": info.get("webpage_url", url),
        }


def prepare_local_audio(input_file_path: Path) -> Dict[str, Any]:
    """
    Extracts metadata from a local audio or video file and returns its specs.
    PyAV / Faster-Whisper natively decodes most formats directly.
    """
    import av

    try:
        container = av.open(str(input_file_path))
        duration = float(container.duration / av.time_base) if container.duration else 0.0
        container.close()
    except Exception:
        duration = 0.0

    file_id = input_file_path.stem
    return {
        "id": file_id,
        "title": input_file_path.name,
        "uploader": "Local File",
        "duration": duration,
        "duration_formatted": format_duration(duration),
        "thumbnail": "",
        "audio_path": str(input_file_path.resolve()),
        "webpage_url": "",
    }
