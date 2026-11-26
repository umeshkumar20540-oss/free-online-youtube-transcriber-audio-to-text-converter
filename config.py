"""
Application configuration and device capability detection.
"""

import os
from pathlib import Path
from typing import Dict, Any, List

# Base Directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
AUDIO_CACHE_DIR = DATA_DIR / "audio_cache"
MODELS_CACHE_DIR = DATA_DIR / "models"
DB_PATH = DATA_DIR / "transcriptions.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
MODELS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# App Metadata
APP_TITLE = "WhisperFlow Local Transcriber"
APP_VERSION = "1.0.0"
APP_HOST = "127.0.0.1"
APP_PORT = 8000

# Whisper Models configuration
AVAILABLE_MODELS = {
    "tiny": {
        "name": "Tiny",
        "size_mb": 75,
        "vram_required": "~1 GB",
        "speed": "Ultra Fast (32x)",
        "description": "Lightest model, ideal for quick drafts and low-spec machines.",
    },
    "base": {
        "name": "Base",
        "size_mb": 145,
        "vram_required": "~1 GB",
        "speed": "Very Fast (16x)",
        "description": "Fast and lightweight with good accuracy for clear audio.",
    },
    "small": {
        "name": "Small",
        "size_mb": 480,
        "vram_required": "~2 GB",
        "speed": "Fast (6x)",
        "description": "Great balance between accuracy and resource usage.",
    },
    "medium": {
        "name": "Medium",
        "size_mb": 1500,
        "vram_required": "~4 GB",
        "speed": "Moderate (2x)",
        "description": "High accuracy for complex speech, accents, and multiple speakers.",
    },
    "large-v3-turbo": {
        "name": "Large v3 Turbo",
        "size_mb": 1600,
        "vram_required": "~4-6 GB",
        "speed": "High Accuracy & Fast (8x)",
        "description": "OpenAI's latest optimized large model: v3 accuracy with 8x speed.",
    },
    "large-v3": {
        "name": "Large v3",
        "size_mb": 3100,
        "vram_required": "~6 GB",
        "speed": "Highest Accuracy (1x)",
        "description": "State-of-the-art accuracy across 99+ languages.",
    },
}

DEFAULT_MODEL = "base"

# Languages supported by Whisper
SUPPORTED_LANGUAGES = [
    {"code": "auto", "name": "Auto Detect"},
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Spanish"},
    {"code": "fr", "name": "French"},
    {"code": "de", "name": "German"},
    {"code": "it", "name": "Italian"},
    {"code": "pt", "name": "Portuguese"},
    {"code": "ja", "name": "Japanese"},
    {"code": "zh", "name": "Chinese"},
    {"code": "ko", "name": "Korean"},
    {"code": "hi", "name": "Hindi"},
    {"code": "ar", "name": "Arabic"},
    {"code": "ru", "name": "Russian"},
    {"code": "nl", "name": "Dutch"},
    {"code": "pl", "name": "Polish"},
    {"code": "tr", "name": "Turkish"},
    {"code": "uk", "name": "Ukrainian"},
    {"code": "vi", "name": "Vietnamese"},
    {"code": "id", "name": "Indonesian"},
    {"code": "th", "name": "Thai"},
    {"code": "sv", "name": "Swedish"},
    {"code": "da", "name": "Danish"},
    {"code": "fi", "name": "Finnish"},
    {"code": "no", "name": "Norwegian"},
    {"code": "el", "name": "Greek"},
    {"code": "he", "name": "Hebrew"},
    {"code": "cs", "name": "Czech"},
    {"code": "ro", "name": "Romanian"},
    {"code": "hu", "name": "Hungarian"},
    {"code": "bn", "name": "Bengali"},
    {"code": "ta", "name": "Tamil"},
    {"code": "te", "name": "Telugu"},
    {"code": "mr", "name": "Marathi"},
    {"code": "ur", "name": "Urdu"},
    {"code": "fa", "name": "Persian"},
]


def detect_hardware() -> Dict[str, Any]:
    """Detects available hardware capabilities (CUDA GPU vs CPU)."""
    device = "cpu"
    compute_type = "int8"
    gpu_name = "None"
    cuda_available = False

    try:
        import ctranslate2
        cuda_count = ctranslate2.get_cuda_device_count()
        if cuda_count > 0:
            device = "cuda"
            cuda_available = True
            supported_types = ctranslate2.get_supported_compute_types("cuda")
            # float16 is optimal for modern NVIDIA GPUs (RTX 3060 etc.)
            if "float16" in supported_types:
                compute_type = "float16"
            elif "int8_float16" in supported_types:
                compute_type = "int8_float16"
            elif "int8" in supported_types:
                compute_type = "int8"

            # Check for GPU device name if PyTorch or nvidia-smi can tell us
            try:
                import subprocess
                res = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if res.returncode == 0 and res.stdout.strip():
                    gpu_name = res.stdout.strip().split("\n")[0]
            except Exception:
                gpu_name = "NVIDIA CUDA GPU"
    except Exception as e:
        device = "cpu"
        compute_type = "int8"

    return {
        "device": device,
        "compute_type": compute_type,
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "cpu_threads": os.cpu_count() or 4
    }
