import { configureStore } from "@reduxjs/toolkit";
import complaintsReducer from "./complaintsSlice";
import copilotReducer from "./copilotSlice";

export const store = configureStore({
  reducer: {
    complaints: complaintsReducer,
    copilot: copilotReducer,
  },
});
