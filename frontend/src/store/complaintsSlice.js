import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import * as api from "../api/client";

export const fetchComplaints = createAsyncThunk("complaints/fetchAll", async () => {
  return await api.listComplaints();
});

export const fetchComplaint = createAsyncThunk("complaints/fetchOne", async (id) => {
  return await api.getComplaint(id);
});

export const submitComplaint = createAsyncThunk(
  "complaints/submit",
  async ({ raw_text, source_channel }) => {
    return await api.createComplaint(raw_text, source_channel);
  }
);

export const changeStatus = createAsyncThunk(
  "complaints/changeStatus",
  async ({ id, status, note }) => {
    return await api.updateStatus(id, status, note);
  }
);

export const editFields = createAsyncThunk(
  "complaints/editFields",
  async ({ id, fields }) => {
    return await api.updateFields(id, fields);
  }
);

export const rerunAi = createAsyncThunk("complaints/rerunAi", async (id) => {
  return await api.rerunAi(id);
});

const complaintsSlice = createSlice({
  name: "complaints",
  initialState: {
    items: [],
    current: null,
    status: "idle",
    submitStatus: "idle",
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchComplaints.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchComplaints.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.items = action.payload;
      })
      .addCase(fetchComplaints.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message;
      })
      .addCase(fetchComplaint.fulfilled, (state, action) => {
        state.current = action.payload;
      })
      .addCase(submitComplaint.pending, (state) => {
        state.submitStatus = "loading";
      })
      .addCase(submitComplaint.fulfilled, (state, action) => {
        state.submitStatus = "succeeded";
        state.items.unshift(action.payload);
        state.current = action.payload;
      })
      .addCase(submitComplaint.rejected, (state, action) => {
        state.submitStatus = "failed";
        state.error = action.error.message;
      })
      .addCase(changeStatus.fulfilled, (state, action) => {
        state.current = action.payload;
        const idx = state.items.findIndex((c) => c.id === action.payload.id);
        if (idx !== -1) state.items[idx] = action.payload;
      })
      .addCase(editFields.fulfilled, (state, action) => {
        state.current = action.payload;
      })
      .addCase(rerunAi.fulfilled, (state, action) => {
        state.current = action.payload;
      });
  },
});

export default complaintsSlice.reducer;
