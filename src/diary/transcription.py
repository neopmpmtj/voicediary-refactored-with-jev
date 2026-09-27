import logging
from pathlib import Path

from decouple import config
from openai import OpenAI

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    pass


def transcribe_audio(audio_path):
    api_key = config("AI_OPENAI_API_KEY", default="")
    if not api_key:
        raise TranscriptionError("AI_OPENAI_API_KEY is not set")
    model = config("TRANSCRIPTION_MODEL", default="gpt-4o-transcribe")
    prompt = config("AI_TRANSCRIPTION_PROMPT", default="").strip()
    client = OpenAI(api_key=api_key, timeout=120.0)
    path = Path(audio_path)
    logger.info("Starting transcription file=%s model=%s", path.name, model)
    with path.open("rb") as audio_file:
        kwargs = {
            "model": model,
            "file": audio_file,
            "response_format": "json",
        }
        if prompt:
            kwargs["prompt"] = prompt
        response = client.audio.transcriptions.create(**kwargs)
    payload = response.model_dump() if hasattr(response, "model_dump") else {}
    text = payload.get("text") or getattr(response, "text", "") or ""
    duration = payload.get("duration")
    return {"text": text, "duration": duration, "model": model}
