"""Whisper ASR service using Groq's Whisper API.

No local model required — runs on Groq's servers for fast, accurate transcription.
"""

import io
import numpy as np
from groq import Groq
from ..config import GROQ_API_KEY

_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Whisper model to use on Groq (whisper-large-v3 is the default, whisper-large-v3-turbo is faster)
_WHISPER_MODEL = "whisper-large-v3"


def transcribe(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """Transcribe a float32 mono audio array (16 kHz) to text via Groq Whisper API.

    Returns the transcribed text (empty string if nothing detected).
    """
    if _client is None:
        raise RuntimeError("GROQ_API_KEY not configured")

    # Convert float32 numpy array to WAV bytes
    import struct
    import wave

    audio_int16 = (audio * 32767).astype(np.int16)
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    wav_buffer.seek(0)
    wav_buffer.name = "audio.wav"

    try:
        result = _client.audio.transcriptions.create(
            file=(wav_buffer.name, wav_buffer.read()),
            model=_WHISPER_MODEL,
            language="en",
        )
        return result.text.strip()
    except Exception as e:
        raise RuntimeError(f"Groq Whisper transcription failed: {e}")
