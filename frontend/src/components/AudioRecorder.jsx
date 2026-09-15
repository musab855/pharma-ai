import React, { useRef, useEffect, useCallback, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  setConnected,
  setRecording,
  setSpeaking,
  addChunk,
  setAnalysis,
  setProcessing,
  setError,
  clearSession,
} from "../store/transcriptionSlice";
import client from "../api/client";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";
const WS_URL = API_BASE.replace(/^http/, "ws") + "/api/transcription/ws";
const FRAME_SIZE = 480; // 30ms at 16kHz — matches backend webrtcvad
const SCRIPT_BUFFER_SIZE = 512; // must be power of 2 for createScriptProcessor

export default function AudioRecorder() {
  const dispatch = useDispatch();
  const { isRecording, fullTranscript, status, wordCount, chunkCount } =
    useSelector((s) => s.transcription);

  const wsRef = useRef(null);
  const audioCtxRef = useRef(null);
  const streamRef = useRef(null);
  const scriptProcessorRef = useRef(null);
  const [statusMsg, setStatusMsg] = useState(
    "Ready — click Start Mic and speak naturally. VAD will auto-chunk your speech."
  );

  const cleanup = useCallback(() => {
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close();
      wsRef.current = null;
    }
    dispatch(setConnected(false));
    dispatch(setRecording(false));
  }, [dispatch]);

  const connectWebSocket = useCallback(() => {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(WS_URL);
      ws.binaryType = "arraybuffer";

      ws.onopen = () => {
        wsRef.current = ws;
        dispatch(setConnected(true));
        resolve(ws);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "transcript") {
            dispatch(addChunk({ text: data.text }));
          } else if (data.type === "vad_status") {
            dispatch(setSpeaking(data.speaking));
          } else if (data.type === "error") {
            dispatch(setError(data.message));
          }
        } catch (e) {
          console.error("WS parse error:", e);
        }
      };

      ws.onerror = (err) => {
        console.error("WS error:", err);
        reject(err);
      };

      ws.onclose = () => {
        dispatch(setConnected(false));
      };
    });
  }, [dispatch]);

  const startRecording = useCallback(async () => {
    try {
      dispatch(clearSession());

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setStatusMsg("Microphone not supported in this browser. Use Chrome or Edge.");
        return;
      }

      setStatusMsg("Requesting microphone access...");
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log("[DEBUG] Mic access granted, tracks:", stream.getTracks().length);
      } catch (micErr) {
        console.error("[DEBUG] Mic error:", micErr.name, micErr.message);
        if (micErr.name === "NotAllowedError") {
          setStatusMsg("Mic blocked by browser. Click the mic icon in the address bar → Allow, then refresh.");
        } else if (micErr.name === "NotFoundError") {
          setStatusMsg("No microphone found. Plug in a mic and try again.");
        } else {
          setStatusMsg("Mic error: " + micErr.name + " - " + micErr.message);
        }
        return;
      }

      setStatusMsg("Connecting to server...");
      let ws;
      try {
        ws = await connectWebSocket();
        console.log("[DEBUG] WebSocket connected");
      } catch (wsErr) {
        console.error("[DEBUG] WebSocket error:", wsErr);
        setStatusMsg("WebSocket connection failed: " + wsErr.message);
        stream.getTracks().forEach(t => t.stop());
        return;
      }
      streamRef.current = stream;

      let audioCtx;
      try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        console.log("[DEBUG] AudioContext created, sampleRate:", audioCtx.sampleRate);
        audioCtxRef.current = audioCtx;
      } catch (ctxErr) {
        console.error("[DEBUG] AudioContext error:", ctxErr);
        setStatusMsg("Audio context failed: " + ctxErr.message);
        cleanup();
        return;
      }
      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(SCRIPT_BUFFER_SIZE, 1, 1);
      scriptProcessorRef.current = processor;

      let residualBuffer = new Float32Array(0);

      processor.onaudioprocess = (event) => {
        if (ws.readyState !== WebSocket.OPEN) return;

        const input = event.inputBuffer.getChannelData(0);
        const ratio = audioCtx.sampleRate / 16000;
        let samples;
        if (Math.abs(ratio - 1) < 0.01) {
          samples = new Float32Array(input);
        } else {
          const newLen = Math.round(input.length / ratio);
          samples = new Float32Array(newLen);
          for (let i = 0; i < newLen; i++) {
            const srcIdx = i * ratio;
            const lo = Math.floor(srcIdx);
            const hi = Math.min(lo + 1, input.length - 1);
            const frac = srcIdx - lo;
            samples[i] = input[lo] * (1 - frac) + input[hi] * frac;
          }
        }

        let offset = 0;
        while (offset + FRAME_SIZE <= samples.length) {
          const frame = samples.slice(offset, offset + FRAME_SIZE);
          ws.send(frame.buffer);
          offset += FRAME_SIZE;
        }

        if (offset < samples.length) {
          const remain = samples.slice(offset);
          const merged = new Float32Array(residualBuffer.length + remain.length);
          merged.set(residualBuffer, 0);
          merged.set(remain, residualBuffer.length);
          residualBuffer = merged;

          while (residualBuffer.length >= FRAME_SIZE) {
            const frame = residualBuffer.slice(0, FRAME_SIZE);
            ws.send(frame.buffer);
            residualBuffer = residualBuffer.slice(FRAME_SIZE);
          }
        }
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      dispatch(setRecording(true));
      setStatusMsg("Listening... speak naturally. VAD will auto-chunk your speech.");
    } catch (err) {
      console.error("Failed to start recording:", err);
      dispatch(setError(err.message || "Failed to access microphone"));
      setStatusMsg("Microphone access denied or unavailable.");
      cleanup();
    }
  }, [connectWebSocket, dispatch, cleanup]);

  const stopRecording = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end_session" }));
    }
    cleanup();
    setStatusMsg("Recording stopped. Click 'Process Transcript with AI' to analyze.");
  }, [cleanup]);

  const handleClear = useCallback(() => {
    cleanup();
    dispatch(clearSession());
    setStatusMsg("Ready — click Start Mic and speak naturally. VAD will auto-chunk your speech.");
  }, [cleanup, dispatch]);

  const handleProcess = useCallback(async () => {
    if (!fullTranscript.trim()) {
      setStatusMsg("No transcript to process. Record something first.");
      return;
    }
    dispatch(setProcessing());
    setStatusMsg("Analyzing transcript with AI...");
    try {
      const { data } = await client.post("/api/transcription/analyze", {
        transcript: fullTranscript,
      });
      dispatch(setAnalysis(data));
      setStatusMsg("Analysis complete.");
    } catch (err) {
      dispatch(setError(err.message || "Analysis failed"));
      setStatusMsg("Analysis failed. Try again.");
    }
  }, [fullTranscript, dispatch]);

  const handleSave = useCallback(() => {
    if (!fullTranscript.trim()) return;
    const blob = new Blob([fullTranscript], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transcript-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [fullTranscript]);

  useEffect(() => {
    return () => cleanup();
  }, [cleanup]);

  return (
    <div className="transcription-left">
      <div className="card transcription-card">
        <div className="card-header">
          <div className="card-title">
            <span className="card-icon">&#x1F52C;</span> Live Medical Transcription
          </div>
          <div className="card-actions">
            <button
              className={`btn btn-start ${isRecording ? "active" : ""}`}
              onClick={startRecording}
              disabled={isRecording}
            >
              &#x1F3A4; Start Mic
            </button>
            <button
              className="btn btn-stop"
              onClick={stopRecording}
              disabled={!isRecording}
            >
              &#x1F534; Stop
            </button>
            <button className="btn btn-secondary" onClick={handleClear}>
              &#x1F5D1; Clear
            </button>
            <button className="btn btn-secondary" onClick={handleSave}>
              &#x1F4BE; Save Recording
            </button>
          </div>
        </div>

        <div className="stats-bar">
          <span className="stat">WORDS: {wordCount}</span>
          <span className="stat">CHUNKS: {chunkCount}</span>
        </div>

        <div className="transcript-output">
          {fullTranscript || (
            <span className="transcript-placeholder">
              Transcript will appear here as you speak...
            </span>
          )}
        </div>

        <div className="transcript-status">
          <span className="status-icon">&#x2705;</span> {statusMsg}
        </div>

        <button
          className="btn btn-process"
          onClick={handleProcess}
          disabled={status === "processing" || !fullTranscript.trim()}
        >
          &#x26A1; Process Transcript with AI
        </button>
      </div>
    </div>
  );
}
