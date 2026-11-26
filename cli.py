"""
Command-Line Interface for WhisperFlow YouTube Transcriber.
Transcribes YouTube URLs or local audio files directly from the terminal.
"""

import os
import sys
import argparse
from pathlib import Path

from config import DEFAULT_MODEL, AVAILABLE_MODELS, detect_hardware
from ffmpeg_utils import ensure_ffmpeg_on_path
from downloader import is_valid_youtube_url, get_video_info, download_youtube_audio, prepare_local_audio
from transcriber import WhisperEngine
import exporters
from summarizer import generate_offline_summary


def main():
    ensure_ffmpeg_on_path()

    parser = argparse.ArgumentParser(
        description="WhisperFlow CLI: Fast local YouTube video and audio transcription powered by Faster-Whisper."
    )
    parser.add_argument("source", help="YouTube URL or local audio/video file path")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=list(AVAILABLE_MODELS.keys()), help="Whisper model size")
    parser.add_argument("--language", default=None, help="Audio language code (e.g. en, es, fr, ja). Default: auto-detect")
    parser.add_argument("--task", default="transcribe", choices=["transcribe", "translate"], help="transcribe or translate to English")
    parser.add_argument("--format", default="all", choices=["all", "txt", "srt", "vtt", "json", "csv", "md"], help="Output export format")
    parser.add_argument("--output-dir", default="./transcripts", help="Directory where exported files will be saved")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"], help="Inference device")
    parser.add_argument("--no-vad", action="store_true", help="Disable Silero VAD voice activity filter")
    parser.add_argument("--no-words", action="store_true", help="Disable word-level timestamps")

    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print(" WhisperFlow - Local Faster-Whisper Transcriber   ")
    print("==================================================")

    # 1. Ingestion
    if is_valid_youtube_url(args.source):
        print(f"\n[1/3] Fetching YouTube info for: {args.source}")
        info = get_video_info(args.source)
        print(f"      Title:    {info['title']}")
        print(f"      Channel:  {info['uploader']}")
        print(f"      Duration: {info['duration_formatted']}")

        print(f"\n[2/3] Downloading audio stream...")
        def dl_progress(pct, speed, eta):
            sys.stdout.write(f"\r      Downloading: {pct:.1f}% ({speed}, ETA {eta})")
            sys.stdout.flush()

        media = download_youtube_audio(args.source, progress_callback=dl_progress)
        print("\n      Download completed successfully!")
        audio_path = media["audio_path"]
        title = media["title"]
        uploader = media["uploader"]
        duration = media["duration"]
        url = args.source
    else:
        file_path = Path(args.source)
        if not file_path.exists():
            print(f"Error: Specified source file does not exist: {args.source}")
            sys.exit(1)
        print(f"\n[1/3] Preparing local file: {file_path.name}")
        media = prepare_local_audio(file_path)
        audio_path = media["audio_path"]
        title = media["title"]
        uploader = "Local File"
        duration = media["duration"]
        url = ""

    # 2. Transcription
    print(f"\n[3/3] Loading Whisper model '{args.model}' and transcribing...")
    engine = WhisperEngine.get_instance()

    stream = engine.transcribe_stream(
        audio_path=audio_path,
        model_size=args.model,
        language=args.language,
        task=args.task,
        vad_filter=not args.no_vad,
        word_timestamps=not args.no_words,
        device=args.device
    )

    final_result = None
    for item in stream:
        if item["type"] == "info":
            print(f"      Detected Language: {item['detected_language']} ({item['language_probability'] * 100:.1f}%)")
            print(f"      Hardware Used:     {item['device_used'].upper()} ({item['compute_type']})")
            print("-" * 50)
        elif item["type"] == "segment":
            seg = item["segment"]
            sys.stdout.write(f"\r[{item['progress']:.1f}%] [{seg['start']:.2f}s -> {seg['end']:.2f}s] {seg['text'][:60]}...")
            sys.stdout.flush()
        elif item["type"] == "completed":
            final_result = item

    print("\n" + "=" * 50)
    print(" Transcription Completed Successfully! ")
    print("=" * 50)

    # 3. Summarization
    summary = generate_offline_summary(final_result["full_text"], final_result["segments"])

    record = {
        "title": title,
        "uploader": uploader,
        "url": url,
        "duration": duration,
        "language": final_result["detected_language"],
        "model_used": args.model,
        "full_text": final_result["full_text"],
        "segments": final_result["segments"],
        "summary": summary
    }

    # 4. Exports
    safe_slug = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title)[:40]
    formats_to_export = [args.format] if args.format != "all" else ["txt", "srt", "vtt", "json", "csv", "md"]

    print("\nSaving exports to:", out_dir.resolve())
    for fmt in formats_to_export:
        dest_file = out_dir / f"{safe_slug}.{fmt}"
        if fmt == "txt":
            content = exporters.export_txt(final_result["segments"], with_timestamps=True)
        elif fmt == "srt":
            content = exporters.export_srt(final_result["segments"])
        elif fmt == "vtt":
            content = exporters.export_vtt(final_result["segments"])
        elif fmt == "json":
            content = exporters.export_json(record)
        elif fmt == "csv":
            content = exporters.export_csv(final_result["segments"])
        elif fmt == "md":
            content = exporters.export_markdown(record)
        else:
            continue

        dest_file.write_text(content, encoding="utf-8")
        print(f"  [OK] {dest_file.name}")

    print("\nAll done!")


if __name__ == "__main__":
    main()
