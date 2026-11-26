"""
FFmpeg resolution utility.
Locates or provides FFmpeg binary using imageio-ffmpeg fallback so the application
runs out-of-the-box on Windows without manual PATH configurations.
"""

import os
import shutil
import subprocess
from pathlib import Path


def get_ffmpeg_path() -> str:
    """
    Returns the path to a usable ffmpeg executable.
    Checks:
    1. System PATH
    2. Local project bin directory
    3. imageio-ffmpeg bundled binary
    """
    # 1. System PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg and os.path.exists(system_ffmpeg):
        return system_ffmpeg

    # 2. Local bin directory
    local_bin_ffmpeg = Path(__file__).resolve().parent / "bin" / "ffmpeg.exe"
    if local_bin_ffmpeg.exists():
        return str(local_bin_ffmpeg)

    # 3. imageio-ffmpeg
    try:
        import imageio_ffmpeg
        img_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        if img_ffmpeg and os.path.exists(img_ffmpeg):
            # Ensure the directory containing this ffmpeg is added to os.environ["PATH"]
            ffmpeg_dir = str(Path(img_ffmpeg).parent)
            if ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
            return img_ffmpeg
    except ImportError:
        pass

    return "ffmpeg"


def ensure_ffmpeg_on_path():
    """Ensures FFmpeg executable directory is on the system PATH."""
    ffmpeg_exe = get_ffmpeg_path()
    if os.path.exists(ffmpeg_exe):
        ffmpeg_dir = str(Path(ffmpeg_exe).parent)
        if ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    return ffmpeg_exe


# Auto-configure path upon import
ensure_ffmpeg_on_path()

# Suppress Hugging Face symlink warning on Windows non-admin shells
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Defensive compatibility patch for PyAV if newer version without metadata_errors is used
try:
    import av
    if hasattr(av, "open"):
        _orig_av_open = av.open
        def _safe_av_open(*args, **kwargs):
            try:
                return _orig_av_open(*args, **kwargs)
            except TypeError as te:
                if "metadata_errors" in str(te):
                    kwargs.pop("metadata_errors", None)
                    return _orig_av_open(*args, **kwargs)
                raise
        av.open = _safe_av_open
except Exception:
    pass

