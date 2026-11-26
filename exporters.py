"""
Multi-format exporters for Whisper transcriptions.
Supports TXT, SRT, VTT, JSON, CSV, and Markdown.
"""

import csv
import io
import json
from typing import List, Dict, Any, Optional


def seconds_to_srt_time(seconds: float) -> str:
    """Converts seconds into SRT format: HH:MM:SS,mmm"""
    if seconds < 0:
        seconds = 0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def seconds_to_vtt_time(seconds: float) -> str:
    """Converts seconds into WebVTT format: HH:MM:SS.mmm"""
    if seconds < 0:
        seconds = 0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"


def seconds_to_hms(seconds: float) -> str:
    """Converts seconds to HH:MM:SS or MM:SS."""
    if seconds < 0:
        seconds = 0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def export_txt(segments: List[Dict[str, Any]], with_timestamps: bool = False) -> str:
    """Exports transcript to plain text."""
    if not with_timestamps:
        return "\n\n".join(seg["text"] for seg in segments if seg.get("text"))
    
    lines = []
    for seg in segments:
        ts = seconds_to_hms(seg.get("start", 0))
        lines.append(f"[{ts}] {seg.get('text', '')}")
    return "\n".join(lines)


def export_srt(segments: List[Dict[str, Any]]) -> str:
    """Exports transcript to SubRip (.srt) subtitle format."""
    blocks = []
    for i, seg in enumerate(segments, start=1):
        start = seconds_to_srt_time(seg.get("start", 0.0))
        end = seconds_to_srt_time(seg.get("end", 0.0))
        text = seg.get("text", "").strip()
        blocks.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(blocks).strip() + "\n"


def export_vtt(segments: List[Dict[str, Any]]) -> str:
    """Exports transcript to WebVTT (.vtt) format."""
    lines = ["WEBVTT", ""]
    for i, seg in enumerate(segments, start=1):
        start = seconds_to_vtt_time(seg.get("start", 0.0))
        end = seconds_to_vtt_time(seg.get("end", 0.0))
        text = seg.get("text", "").strip()
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def export_json(data: Dict[str, Any]) -> str:
    """Exports transcript to clean JSON."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def export_csv(segments: List[Dict[str, Any]]) -> str:
    """Exports transcript segments into CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "start_seconds", "end_seconds", "start_timestamp", "end_timestamp", "text"])
    
    for i, seg in enumerate(segments, start=1):
        start = seg.get("start", 0.0)
        end = seg.get("end", 0.0)
        writer.writerow([
            i,
            round(start, 2),
            round(end, 2),
            seconds_to_hms(start),
            seconds_to_hms(end),
            seg.get("text", "")
        ])
    return output.getvalue()


def export_markdown(record: Dict[str, Any]) -> str:
    """Exports transcript with metadata header in Markdown (.md) format."""
    title = record.get("title", "YouTube Video Transcript")
    url = record.get("url", "")
    author = record.get("uploader", "Unknown")
    duration = seconds_to_hms(record.get("duration", 0))
    language = record.get("language", "Auto")
    model = record.get("model_used", "Faster-Whisper")
    segments = record.get("segments", [])
    summary = record.get("summary", "")

    md = [
        f"# {title}",
        "",
        f"- **Channel / Uploader:** {author}",
        f"- **Duration:** {duration}",
        f"- **Language:** {language}",
        f"- **Model:** {model}",
    ]
    if url:
        md.append(f"- **Source URL:** [{url}]({url})")
    md.append("")

    if summary:
        md.extend([
            "## Summary & Key Takeaways",
            "",
            summary,
            "",
            "---",
            ""
        ])

    md.extend(["## Full Transcript", ""])
    for seg in segments:
        ts = seconds_to_hms(seg.get("start", 0))
        text = seg.get("text", "").strip()
        md.append(f"> **`{ts}`** {text}")
        md.append("")

    return "\n".join(md)
