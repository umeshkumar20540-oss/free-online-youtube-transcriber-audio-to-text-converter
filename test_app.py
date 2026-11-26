"""
Automated unit and integration test suite for WhisperFlow.
Tests exporters, database storage, summarizer, audio pipeline, and faster-whisper inference.
"""

import os
import sys
import json
import wave
import struct
import math
from pathlib import Path

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

import exporters
import storage
import summarizer
from ffmpeg_utils import get_ffmpeg_path
from config import detect_hardware, AVAILABLE_MODELS
from transcriber import WhisperEngine


def test_exporters():
    print("Testing exporters...")
    mock_segments = [
        {
            "id": 1,
            "start": 0.0,
            "end": 2.5,
            "text": "Hello world.",
            "words": [
                {"word": "Hello", "start": 0.0, "end": 1.0, "probability": 0.98},
                {"word": "world.", "start": 1.0, "end": 2.5, "probability": 0.95}
            ]
        },
        {
            "id": 2,
            "start": 2.6,
            "end": 5.8,
            "text": "This is Faster Whisper in action.",
            "words": []
        }
    ]
    mock_record = {
        "title": "Test Video",
        "uploader": "Test Channel",
        "url": "https://www.youtube.com/watch?v=12345678901",
        "duration": 5.8,
        "language": "en",
        "model_used": "base",
        "segments": mock_segments,
        "summary": "This is a summary."
    }

    # Test SRT
    srt_out = exporters.export_srt(mock_segments)
    assert "00:00:00,000 --> 00:00:02,500" in srt_out, f"SRT start time mismatch: {srt_out}"
    assert "Hello world." in srt_out

    # Test VTT
    vtt_out = exporters.export_vtt(mock_segments)
    assert "WEBVTT" in vtt_out
    assert "00:00:00.000 --> 00:00:02.500" in vtt_out

    # Test TXT
    txt_out = exporters.export_txt(mock_segments, with_timestamps=True)
    assert "[00:00] Hello world." in txt_out

    # Test JSON
    json_out = exporters.export_json(mock_record)
    parsed = json.loads(json_out)
    assert parsed["title"] == "Test Video"
    assert len(parsed["segments"]) == 2

    # Test CSV
    csv_out = exporters.export_csv(mock_segments)
    assert "id,start_seconds,end_seconds" in csv_out
    assert "Hello world." in csv_out

    # Test Markdown
    md_out = exporters.export_markdown(mock_record)
    assert "# Test Video" in md_out
    assert "Test Channel" in md_out

    print("[OK] All exporter tests passed!")


def test_storage():
    print("Testing SQLite storage...")
    storage.init_db()

    test_id = "test_record_123"
    test_data = {
        "id": test_id,
        "title": "Database Test Video",
        "uploader": "Tester",
        "source_type": "youtube",
        "url": "https://youtube.com/watch?v=test",
        "duration": 120.5,
        "thumbnail": "https://example.com/thumb.jpg",
        "model_used": "base",
        "language": "en",
        "full_text": "This is a test transcription saved to sqlite.",
        "segments": [{"id": 1, "start": 0.0, "end": 2.0, "text": "This is a test"}],
        "audio_path": "",
        "summary": "Summary of test."
    }

    saved_id = storage.save_transcription(test_data)
    assert saved_id == test_id

    # Retrieve
    retrieved = storage.get_transcription(test_id)
    assert retrieved is not None
    assert retrieved["title"] == "Database Test Video"
    assert len(retrieved["segments"]) == 1

    # List
    items = storage.list_transcriptions(search_query="Database Test")
    assert any(item["id"] == test_id for item in items)

    # Delete
    del_ok = storage.delete_transcription(test_id)
    assert del_ok is True
    assert storage.get_transcription(test_id) is None

    print("[OK] All storage tests passed!")


def test_summarizer():
    print("Testing summarizer...")
    text = (
        "Welcome to this lecture on artificial intelligence. Today we will cover neural networks, "
        "faster whisper, and deep learning architectures. Deep learning has revolutionized modern "
        "speech recognition by allowing models to translate audio directly into text without complex "
        "manual feature pipelines. Faster Whisper implements CTranslate2 to achieve high inference speed. "
        "In conclusion, these techniques represent the future of speech transcription."
    )
    segments = [
        {"start": 0.0, "end": 10.0, "text": "Welcome to this lecture on artificial intelligence."},
        {"start": 10.5, "end": 25.0, "text": "Today we will cover neural networks, faster whisper, and deep learning architectures."},
        {"start": 30.0, "end": 50.0, "text": "Faster Whisper implements CTranslate2 to achieve high inference speed."},
        {"start": 55.0, "end": 70.0, "text": "In conclusion, these techniques represent the future of speech transcription."}
    ]

    summary = summarizer.generate_offline_summary(text, segments)
    assert "Executive Highlights" in summary
    assert "Key Topics" in summary
    print("[OK] All summarizer tests passed!")


def test_ffmpeg_and_hardware():
    print("Testing FFmpeg & Hardware Detection...")
    ffmpeg_path = get_ffmpeg_path()
    assert os.path.exists(ffmpeg_path), f"FFmpeg not found at {ffmpeg_path}"
    print(f"  FFmpeg located: {ffmpeg_path}")

    hw = detect_hardware()
    print(f"  Device: {hw['device']}, Compute: {hw['compute_type']}, CUDA: {hw['cuda_available']}, GPU: {hw['gpu_name']}")
    assert hw["device"] in ("cuda", "cpu")
    print("[OK] FFmpeg & Hardware checks passed!")


def create_synthetic_wav(path: Path, duration_sec: float = 2.0, freq: float = 440.0):
    """Generates a simple 16kHz sine wave audio file for testing transcription pipeline."""
    sample_rate = 16000
    num_samples = int(duration_sec * sample_rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            value = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            data = struct.pack("<h", value)
            wav_file.writeframes(data)


def test_faster_whisper_inference():
    print("Testing Faster-Whisper model loading and inference...")
    temp_wav = Path("test_sample.wav")
    try:
        create_synthetic_wav(temp_wav, duration_sec=1.5)
        engine = WhisperEngine.get_instance()
        # Use tiny model for quick verification
        stream = engine.transcribe_stream(
            audio_path=str(temp_wav.resolve()),
            model_size="tiny",
            device="auto"
        )
        events = list(stream)
        assert len(events) >= 2, f"Expected at least info and completed events, got {len(events)}"
        info_event = events[0]
        completed_event = events[-1]
        assert info_event["type"] == "info"
        assert completed_event["type"] == "completed"
        print(f"  Inference verified! Device used: {completed_event['device_used']} ({completed_event['compute_type']})")
        print("[OK] Faster-Whisper inference test passed!")
    finally:
        if temp_wav.exists():
            temp_wav.unlink()


if __name__ == "__main__":
    test_exporters()
    test_storage()
    test_summarizer()
    test_ffmpeg_and_hardware()
    test_faster_whisper_inference()
    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

