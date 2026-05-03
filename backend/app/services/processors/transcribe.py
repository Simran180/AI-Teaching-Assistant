"""Audio/video transcription using SpeechRecognition (Google free tier)."""
import subprocess
import tempfile
from pathlib import Path

import speech_recognition as sr

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}


def _convert_to_wav(input_path: str) -> str:
    """Use ffmpeg to convert any audio/video file to 16 kHz mono WAV."""
    output = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    output.close()
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output.name,
        ],
        capture_output=True,
        check=True,
    )
    return output.name


def _transcribe_wav(wav_path: str) -> str:
    """Transcribe a WAV file using Google's free speech recognition."""
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio)


def transcribe_from_bytes(file_bytes: bytes, filename: str) -> str:
    """Write bytes to a temp file, convert to WAV if needed, and transcribe."""
    ext = Path(filename).suffix.lower()

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        if ext == ".wav":
            return _transcribe_wav(tmp_path)

        wav_path = _convert_to_wav(tmp_path)
        try:
            return _transcribe_wav(wav_path)
        finally:
            Path(wav_path).unlink(missing_ok=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
