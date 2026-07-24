import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import client from "../api/client";

export const sendCopilotMessage = createAsyncThunk(
  "copilot/sendMessage",
  async ({ complaintId, message }) => {
    const { data } = await client.post("/api/copilot/message", {
      complaint_id: complaintId || null,
      message,
    });
    return data;
  }
);

export const uploadCopilotFile = createAsyncThunk(
  "copilot/uploadFile",
  async ({ complaintId, file }) => {
    const form = new FormData();
    if (complaintId) form.append("complaint_id", complaintId);
    form.append("file", file);
    const { data } = await client.post("/api/copilot/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  }
);

const copilotSlice = createSlice({
  name: "copilot",
  initialState: {
    messages: [], // {role: 'user'|'assistant', content, tool_used?}
    complaint: null,
    status: "idle",
  },
  reducers: {
    resetCopilot: (state) => {
      state.messages = [];
      state.complaint = null;
      state.status = "idle";
    },
    addUserMessage: (state, action) => {
      state.messages.push({ role: "user", content: action.payload });
    },
    seedMessage: (state, action) => {
      state.messages.push(action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendCopilotMessage.pending, (state) => {
        state.status = "loading";
      })
      .addCase(sendCopilotMessage.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.messages.push({
          role: "assistant",
          content: action.payload.reply,
          tool_used: action.payload.tool_used,
        });
        state.complaint = action.payload.complaint;
      })
      .addCase(sendCopilotMessage.rejected, (state) => {
        state.status = "failed";
        state.messages.push({
          role: "assistant",
          content: "Something went wrong reaching the AI copilot. Please try again.",
        });
      })
      .addCase(uploadCopilotFile.pending, (state) => {
        state.status = "loading";
      })
      .addCase(uploadCopilotFile.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.messages.push({
          role: "assistant",
          content: action.payload.reply,
          tool_used: action.payload.tool_used,
        });
        state.complaint = action.payload.complaint;
      })
      .addCase(uploadCopilotFile.rejected, (state) => {
        state.status = "failed";
        state.messages.push({
          role: "assistant",
          content: "Couldn't process that file. Please try again.",
        });
      });
  },
});

export const { resetCopilot, addUserMessage, seedMessage } = copilotSlice.actions;
export default copilotSlice.reducer;
