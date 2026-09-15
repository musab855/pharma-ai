"""WebSocket + REST endpoints for live medical transcription.

WebSocket flow:
  1. Client connects to /api/transcription/ws
  2. Client sends binary audio frames (float32, 16kHz, 512 samples each)
  3. Server runs VAD, accumulates speech segments, runs Whisper ASR
  4. Server sends JSON messages back:
     - {"type": "transcript", "text": "...", "is_final": bool}
     - {"type": "vad_status", "speaking": bool}
     - {"type": "error", "message": "..."}
  5. Client sends {"type": "end_session"} to close the WebSocket

REST:
  POST /api/transcription/analyze — send a completed transcript, get clinical analysis
"""

import asyncio
import struct
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..transcription.vad import VADDetector, FRAME_SIZE, SAMPLE_RATE
from ..transcription.whisper_service import transcribe
from ..transcription.clinical_analysis import analyze_transcript

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transcription", tags=["transcription"])


# ---------------------------------------------------------------------------
# REST endpoint — analyse a completed transcript (triggered by button click)
# ---------------------------------------------------------------------------

class TranscriptIn(BaseModel):
    transcript: str


@router.post("/analyze")
def analyze(body: TranscriptIn):
    if not body.transcript.strip():
        return {"error": "Empty transcript"}
    return analyze_transcript(body.transcript)


# ---------------------------------------------------------------------------
# WebSocket endpoint — live streaming transcription (no auto-analysis)
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def transcription_ws(websocket: WebSocket):
    await websocket.accept()
    logger.info("Transcription WebSocket connected")

    vad = VADDetector()
    frame_buffer = bytearray()

    try:
        while True:
            message = await websocket.receive()

            # Handle disconnect gracefully
            if message.get("type") == "websocket.disconnect":
                break

            # Text messages are control commands
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type")

                if msg_type == "end_session":
                    # Flush any remaining speech segment
                    remaining = vad.force_flush()
                    if remaining is not None and len(remaining) > 0:
                        text = await asyncio.to_thread(transcribe, remaining)
                        if text:
                            await websocket.send_json({
                                "type": "transcript",
                                "text": text,
                                "is_final": True,
                            })

                    await websocket.send_json({
                        "type": "session_ended",
                    })
                    break

                continue

            # Binary messages are raw audio frames
            if "bytes" in message:
                raw = message["bytes"]
                frame_buffer.extend(raw)

                while len(frame_buffer) >= FRAME_SIZE * 4:
                    chunk_bytes = bytes(frame_buffer[: FRAME_SIZE * 4])
                    frame_buffer = frame_buffer[FRAME_SIZE * 4:]

                    frame = struct.unpack(f"<{FRAME_SIZE}f", chunk_bytes)
                    import numpy as np
                    frame_np = np.array(frame, dtype=np.float32)

                    vad.process_frame(frame_np)

                    segment = vad.check_segment()
                    if segment is not None and len(segment) > 0:
                        text = await asyncio.to_thread(transcribe, segment)
                        if text:
                            await websocket.send_json({
                                "type": "transcript",
                                "text": text,
                                "is_final": True,
                            })

                    await websocket.send_json({
                        "type": "vad_status",
                        "speaking": vad._speech_active,
                    })

    except WebSocketDisconnect:
        logger.info("Transcription WebSocket disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
