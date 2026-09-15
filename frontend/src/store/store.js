import { configureStore } from "@reduxjs/toolkit";
import complaintsReducer from "./complaintsSlice";
import copilotReducer from "./copilotSlice";
import transcriptionReducer from "./transcriptionSlice";

export const store = configureStore({
  reducer: {
    complaints: complaintsReducer,
    copilot: copilotReducer,
    transcription: transcriptionReducer,
  },
});
