"""
Groq Whisper Speech-to-Text API Service Module
------------------------------------------------
Transcribes recorded candidate audio (WAV, WebM, MP3, M4A) using the Groq Whisper API endpoint.
Features:
- Handles short audio, empty transcripts, timeouts, and API error codes gracefully.
- Returns clean (success: bool, transcript_or_error_msg: str) tuple.
"""

import os
import requests


def transcribe_audio_groq(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    api_key: str | None = None,
    model: str = "whisper-large-v3-turbo"
) -> tuple[bool, str]:
    """
    Sends audio bytes to Groq Whisper API endpoint for speech recognition.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return False, "Audio recording is too short. Please speak again clearly."

    key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY", "")
    if not key or not key.strip():
        return False, "Groq API key not configured. Please set GROQ_API_KEY in your environment variables or settings."

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {key.strip()}"
    }

    # Determine mime-type based on file extension
    ext = filename.lower()
    if ext.endswith(".webm"):
        mime_type = "audio/webm"
    elif ext.endswith(".mp3"):
        mime_type = "audio/mp3"
    elif ext.endswith(".m4a"):
        mime_type = "audio/m4a"
    elif ext.endswith(".ogg"):
        mime_type = "audio/ogg"
    else:
        mime_type = "audio/wav"

    files = {
        "file": (filename, audio_bytes, mime_type),
    }
    data = {
        "model": model,
        "response_format": "json",
        "language": "en"
    }

    try:
        response = requests.post(url, headers=headers, files=files, data=data, timeout=25)
        if response.status_code == 200:
            result = response.json()
            text = result.get("text", "").strip()
            if not text:
                return False, "Speech was not recognized clearly. Please try speaking again."
            return True, text
        else:
            return False, f"Groq Whisper API Error ({response.status_code}): {response.text}"
    except requests.exceptions.Timeout:
        return False, "Transcription timed out. Please check your network connection and retry."
    except Exception as exc:
        return False, f"Failed to transcribe voice input: {exc}"
