"""
Faster-Whisper transcription engine.
Provides model caching, CUDA-to-CPU automatic fallback, Silero VAD filtering,
word-level timestamp extraction, and real-time segment streaming.
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Generator
from pathlib import Path

from faster_whisper import WhisperModel

from config import MODELS_CACHE_DIR, DEFAULT_MODEL, detect_hardware

logger = logging.getLogger(__name__)


class WhisperEngine:
    _instance = None

    def __init__(self):
        self.current_model: Optional[WhisperModel] = None
        self.current_model_size: Optional[str] = None
        self.current_device: Optional[str] = None
        self.current_compute_type: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "WhisperEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_or_load_model(
        self,
        model_size: str = DEFAULT_MODEL,
        device: Optional[str] = None,
        compute_type: Optional[str] = None
    ) -> WhisperModel:
        """
        Loads and caches a WhisperModel. Reuses existing model if parameters match.
        Gracefully falls back to CPU if CUDA encounters an issue.
        """
        hardware = detect_hardware()

        if device is None or device == "auto":
            device = hardware["device"]

        if compute_type is None or compute_type == "auto":
            compute_type = hardware["compute_type"] if device == "cuda" else "int8"

        # Check if already loaded with matching configuration
        if (
            self.current_model is not None
            and self.current_model_size == model_size
            and self.current_device == device
            and self.current_compute_type == compute_type
        ):
            return self.current_model

        logger.info(f"Loading WhisperModel: {model_size} on {device} ({compute_type})...")

        try:
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=str(MODELS_CACHE_DIR),
                cpu_threads=hardware["cpu_threads"]
            )
            self.current_model = model
            self.current_model_size = model_size
            self.current_device = device
            self.current_compute_type = compute_type
            return model
        except Exception as e:
            if device == "cuda":
                logger.warning(
                    f"CUDA initialization failed for model {model_size}: {e}. "
                    "Falling back to CPU with int8 quantization."
                )
                model = WhisperModel(
                    model_size,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(MODELS_CACHE_DIR),
                    cpu_threads=hardware["cpu_threads"]
                )
                self.current_model = model
                self.current_model_size = model_size
                self.current_device = "cpu"
                self.current_compute_type = "int8"
                return model
            raise

    def transcribe_stream(
        self,
        audio_path: str,
        model_size: str = DEFAULT_MODEL,
        language: Optional[str] = None,
        task: str = "transcribe",
        vad_filter: bool = True,
        word_timestamps: bool = True,
        initial_prompt: Optional[str] = None,
        temperature: float = 0.0,
        beam_size: int = 5,
        device: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
        """
        Streams transcription progress and segments yielding progress events.
        Final return (or final yielded message) includes the complete transcript.
        """
        model = self.get_or_load_model(model_size=model_size, device=device)

        lang_param = None if (not language or language == "auto") else language

        vad_params = dict(
            min_silence_duration_ms=500,
            speech_pad_ms=200
        ) if vad_filter else None

        try:
            segments_generator, info = model.transcribe(
                audio_path,
                language=lang_param,
                task=task,
                beam_size=beam_size,
                temperature=temperature,
                vad_filter=vad_filter,
                vad_parameters=vad_params,
                word_timestamps=word_timestamps,
                initial_prompt=initial_prompt
            )
        except Exception as e:
            if self.current_device == "cuda":
                logger.warning(f"CUDA execution failed: {e}. Falling back to CPU int8.")
                model = self.get_or_load_model(model_size=model_size, device="cpu", compute_type="int8")
                segments_generator, info = model.transcribe(
                    audio_path,
                    language=lang_param,
                    task=task,
                    beam_size=beam_size,
                    temperature=temperature,
                    vad_filter=vad_filter,
                    vad_parameters=vad_params,
                    word_timestamps=word_timestamps,
                    initial_prompt=initial_prompt
                )
            else:
                raise

        total_duration = info.duration or 1.0

        # Yield initial info
        yield {
            "type": "info",
            "detected_language": info.language,
            "language_probability": round(info.language_probability, 4),
            "duration": total_duration,
            "device_used": self.current_device,
            "compute_type": self.current_compute_type,
        }

        all_segments = []
        full_text_pieces = []

        for segment in segments_generator:
            seg_dict = {
                "id": segment.id,
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
                "words": []
            }

            if word_timestamps and segment.words:
                seg_dict["words"] = [
                    {
                        "word": w.word,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 3)
                    }
                    for w in segment.words
                ]

            all_segments.append(seg_dict)
            full_text_pieces.append(seg_dict["text"])

            progress_pct = min(100.0, round((segment.end / total_duration) * 100.0, 1))

            yield {
                "type": "segment",
                "segment": seg_dict,
                "progress": progress_pct,
                "current_time": round(segment.end, 2),
                "total_time": round(total_duration, 2)
            }

        full_text = " ".join(full_text_pieces).strip()

        result = {
            "type": "completed",
            "detected_language": info.language,
            "language_probability": round(info.language_probability, 4),
            "duration": total_duration,
            "segments": all_segments,
            "full_text": full_text,
            "device_used": self.current_device,
            "compute_type": self.current_compute_type,
            "model_size": self.current_model_size,
        }

        yield result
        return result
