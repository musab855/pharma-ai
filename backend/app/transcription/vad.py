"""Voice Activity Detection using WebRTC VAD.

Detects speech segments in a streaming audio signal so that silence
and background noise are not forwarded to the ASR model.
"""

import webrtcvad
import numpy as np
from collections import deque

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30  # webrtcvad supports 10, 20, or 30ms frames
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # 480 samples at 30ms
SILENCE_TIMEOUT_MS = 1000
PRE_SPEECH_PAD_MS = 300


class VADDetector:
    """Wraps WebRTC VAD for streaming speech segment detection."""

    def __init__(self, aggressiveness: int = 1,
                 silence_timeout_ms: int = SILENCE_TIMEOUT_MS,
                 pre_speech_pad_ms: int = PRE_SPEECH_PAD_MS):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.silence_timeout = silence_timeout_ms
        self.pre_speech_pad = pre_speech_pad_ms

        self._pre_speech_maxlen = int(
            pre_speech_pad_ms / FRAME_DURATION_MS
        )
        self.reset()

    def reset(self):
        self._speech_active = False
        self._silence_frames = 0
        self._pre_speech_buffer = deque(maxlen=self._pre_speech_maxlen)
        self._current_segment_frames = []

    def _pcm_bytes(self, frame: np.ndarray) -> bytes:
        """Convert float32 frame to int16 PCM bytes for webrtcvad."""
        int16 = (frame * 32767).clip(-32768, 32767).astype(np.int16)
        return int16.tobytes()

    def process_frame(self, frame: np.ndarray):
        """Process a single audio frame (float32, 16kHz)."""
        pcm = self._pcm_bytes(frame)
        is_speech = self.vad.is_speech(pcm, SAMPLE_RATE)

        if is_speech:
            if not self._speech_active:
                # Speech started — flush pre-speech buffer into segment
                self._current_segment_frames = list(self._pre_speech_buffer)
                self._speech_active = True
                self._silence_frames = 0
            self._current_segment_frames.append(frame)
            self._pre_speech_buffer.clear()
        else:
            # Silence frame
            self._pre_speech_buffer.append(frame)
            if self._speech_active:
                self._silence_frames += 1

    def check_segment(self) -> np.ndarray | None:
        """Check if enough silence has accumulated to close the speech segment."""
        if not self._speech_active:
            return None

        silence_frames_needed = int(self.silence_timeout / FRAME_DURATION_MS)

        if self._silence_frames >= silence_frames_needed:
            # Trim trailing silence (keep half for natural cutoff)
            trim = min(self._silence_frames // 2, self._silence_frames)
            segment_frames = self._current_segment_frames[:-trim] if trim else self._current_segment_frames
            self._speech_active = False
            self._current_segment_frames = []
            self._silence_frames = 0
            if segment_frames:
                return np.concatenate(segment_frames).astype(np.float32)

        return None

    def force_flush(self) -> np.ndarray | None:
        """Force-flush any in-progress speech segment (e.g. on session end)."""
        if not self._speech_active or not self._current_segment_frames:
            return None
        audio = np.concatenate(self._current_segment_frames).astype(np.float32)
        self._speech_active = False
        self._current_segment_frames = []
        self._silence_frames = 0
        return audio
