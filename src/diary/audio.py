import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

SILENCE_THRESHOLD_DB = -35.0
SILENCE_MIN_DURATION = 0.5


def probe_duration_seconds(path):
    path = Path(path)
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        result = subprocess.run(
            [
                ffprobe, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                return float(result.stdout.strip())
            except ValueError:
                logger.error("Could not parse ffprobe duration: %s", result.stdout)
    return None


def strip_silence(source, dest):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.error("ffmpeg is not installed")
        return False
    audio_filter = (
        "silenceremove="
        "start_periods=0:"
        "stop_periods=-1:"
        f"start_threshold={SILENCE_THRESHOLD_DB}dB:"
        f"stop_threshold={SILENCE_THRESHOLD_DB}dB:"
        f"start_duration={SILENCE_MIN_DURATION}:"
        f"stop_duration={SILENCE_MIN_DURATION}:"
        "detection=peak"
    )
    result = subprocess.run(
        [ffmpeg, "-i", str(source), "-af", audio_filter, "-y", str(dest)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0 or not Path(dest).exists() or Path(dest).stat().st_size == 0:
        logger.error("Silence removal failed: %s", result.stderr[-500:] if result.stderr else "")
        Path(dest).unlink(missing_ok=True)
        return False
    return True
