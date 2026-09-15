import { createSlice } from "@reduxjs/toolkit";

const transcriptionSlice = createSlice({
  name: "transcription",
  initialState: {
    transcriptChunks: [],
    fullTranscript: "",
    wordCount: 0,
    chunkCount: 0,
    isRecording: false,
    isSpeaking: false,
    isConnected: false,
    status: "idle",
    error: null,
    analysis: null,
  },
  reducers: {
    setConnected: (state, action) => {
      state.isConnected = action.payload;
    },
    setRecording: (state, action) => {
      state.isRecording = action.payload;
      if (action.payload) {
        state.status = "recording";
        state.error = null;
      }
    },
    setSpeaking: (state, action) => {
      state.isSpeaking = action.payload;
    },
    addChunk: (state, action) => {
      const text = action.payload.text;
      state.transcriptChunks.push(text);
      state.fullTranscript = state.transcriptChunks.join(" ");
      state.wordCount = state.fullTranscript.split(/\s+/).filter(Boolean).length;
      state.chunkCount = state.transcriptChunks.length;
    },
    setAnalysis: (state, action) => {
      state.analysis = action.payload;
      state.status = "complete";
    },
    setProcessing: (state) => {
      state.status = "processing";
    },
    setError: (state, action) => {
      state.error = action.payload;
      state.status = "error";
    },
    clearSession: (state) => {
      state.transcriptChunks = [];
      state.fullTranscript = "";
      state.wordCount = 0;
      state.chunkCount = 0;
      state.analysis = null;
      state.status = "idle";
      state.error = null;
    },
    resetTranscription: (state) => {
      state.transcriptChunks = [];
      state.fullTranscript = "";
      state.wordCount = 0;
      state.chunkCount = 0;
      state.isRecording = false;
      state.isSpeaking = false;
      state.isConnected = false;
      state.status = "idle";
      state.error = null;
      state.analysis = null;
    },
  },
});

export const {
  setConnected,
  setRecording,
  setSpeaking,
  addChunk,
  setAnalysis,
  setProcessing,
  setError,
  clearSession,
  resetTranscription,
} = transcriptionSlice.actions;

export default transcriptionSlice.reducer;
